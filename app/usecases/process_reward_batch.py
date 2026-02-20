"""Process Reward Batch Use Case — batch processor with Transactional Outbox.

Flow:
1) Select unprocessed reward_batches FOR UPDATE SKIP LOCKED
2) For each batch:
   a) Get or create publisher account
   b) Create ledger entry for publisher reward
   c) Credit publisher balance atomically
   d) Credit treasury account
   e) Credit platform_fee account
   f) Write outbox message (same transaction)
   g) Mark batch processed
All inside a single DB transaction.
"""

from __future__ import annotations

from asyncpg import Pool

from app.core.logging import get_logger
from app.domain.entities.ledger_entry import LedgerEntry
from app.domain.entities.outbox_message import OutboxMessage
from app.domain.repositories.account_repo import AccountRepository
from app.domain.repositories.ledger_repo import LedgerRepository
from app.domain.repositories.outbox_repo import OutboxRepository
from app.domain.repositories.reward_batch_repo import RewardBatchRepository
from app.domain.value_objects.enums import EntryType, TreasuryAccountType
from app.infrastructure.db.repositories.treasury_repo_impl import PgTreasuryRepository
from app.infrastructure.db.transaction import transaction
from app.infrastructure.redis.cache import CacheService

logger = get_logger(__name__)


class ProcessRewardBatchUseCase:
    """Processes unprocessed reward batches — pays publishers and platform."""

    def __init__(
        self,
        pool: Pool,
        account_repo: AccountRepository,
        ledger_repo: LedgerRepository,
        reward_batch_repo: RewardBatchRepository,
        treasury_repo: PgTreasuryRepository,
        outbox_repo: OutboxRepository,
        cache: CacheService | None = None,
    ) -> None:
        self._pool = pool
        self._account_repo = account_repo
        self._ledger_repo = ledger_repo
        self._reward_batch_repo = reward_batch_repo
        self._treasury_repo = treasury_repo
        self._outbox_repo = outbox_repo
        self._cache = cache

    async def execute(self, batch_size: int = 500) -> int:
        """Process up to batch_size unprocessed batches.

        Returns the number of batches processed.
        """
        processed_count = 0

        async with transaction(self._pool) as conn:
            batches = await self._reward_batch_repo.fetch_unprocessed_for_update(
                batch_size, conn
            )

            if not batches:
                return 0

            logger.info("batch_processing_started", count=len(batches))

            for batch in batches:
                # ── 1. Publisher payout ───────────────────
                if batch.total_publisher_reward > 0:
                    publisher_account = (
                        await self._account_repo.get_or_create_by_user_id(
                            batch.publisher_id, conn
                        )
                    )

                    publisher_entry = LedgerEntry.create(
                        account_id=publisher_account.id,
                        amount=batch.total_publisher_reward,
                        entry_type=EntryType.PUBLISHER_REWARD,
                        reference_id=batch.id,
                        metadata={
                            "content_id": str(batch.content_id),
                            "action_code": batch.action_code,
                            "action_count": batch.action_count,
                        },
                    )
                    await self._ledger_repo.append(publisher_entry, conn)

                    publisher_account.credit(batch.total_publisher_reward)
                    await self._account_repo.update_balance(
                        publisher_account.id, publisher_account.balance, conn
                    )

                    if self._cache:
                        await self._cache.invalidate_balance(publisher_account.id)

                # ── 2. Platform fee ──────────────────────
                if batch.total_platform_fee > 0:
                    await self._treasury_repo.credit(
                        TreasuryAccountType.PLATFORM_FEE,
                        batch.total_platform_fee,
                        conn,
                    )

                    platform_entry = LedgerEntry.create(
                        account_id=batch.id,  # reference to batch itself
                        amount=batch.total_platform_fee,
                        entry_type=EntryType.PLATFORM_FEE,
                        reference_id=batch.id,
                        metadata={"account_type": TreasuryAccountType.PLATFORM_FEE},
                    )
                    await self._ledger_repo.append(platform_entry, conn)

                # ── 3. Treasury cut ──────────────────────
                if batch.total_treasury_cut > 0:
                    await self._treasury_repo.credit(
                        TreasuryAccountType.TREASURY,
                        batch.total_treasury_cut,
                        conn,
                    )

                    treasury_entry = LedgerEntry.create(
                        account_id=batch.id,
                        amount=batch.total_treasury_cut,
                        entry_type=EntryType.TREASURY_CUT,
                        reference_id=batch.id,
                        metadata={"account_type": TreasuryAccountType.TREASURY},
                    )
                    await self._ledger_repo.append(treasury_entry, conn)

                # ── 4. Write outbox message (same transaction) ──
                outbox_msg = OutboxMessage.create(
                    aggregate_type="batch_processed",
                    aggregate_id=batch.id,
                    event_type=f"batch.{batch.action_code}.processed",
                    payload={
                        "batch_id": str(batch.id),
                        "publisher_id": str(batch.publisher_id),
                        "content_id": str(batch.content_id),
                        "action_code": batch.action_code,
                        "action_count": batch.action_count,
                        "publisher_reward": batch.total_publisher_reward,
                        "platform_fee": batch.total_platform_fee,
                        "treasury_cut": batch.total_treasury_cut,
                    },
                )
                await self._outbox_repo.insert(outbox_msg, conn)

                # ── 5. Mark processed ────────────────────
                await self._reward_batch_repo.mark_processed(batch.id, conn)
                processed_count += 1

                logger.info(
                    "batch_processed",
                    batch_id=str(batch.id),
                    publisher_reward=batch.total_publisher_reward,
                    platform_fee=batch.total_platform_fee,
                    treasury_cut=batch.total_treasury_cut,
                    action_count=batch.action_count,
                )

        logger.info("batch_processing_completed", processed=processed_count)
        return processed_count
