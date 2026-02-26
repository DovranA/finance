"""Process Reward Event Use Case — core action flow with Transactional Outbox.

Full flow:
1) Idempotency check (Redis short-TTL + DB)
2) Fetch active economic version for action_code
3) Create actor_action record
4) If actor_reward > 0: create ledger entry for actor, update balance
5) Upsert publisher reward into reward_batches
6) Write outbox message (same transaction) for downstream consumers
7) Mark event as processed (DB + Redis)
8) Commit transaction — outbox relay publishes later
"""

from __future__ import annotations

from asyncpg import Pool

from app.core.logging import get_logger
from app.domain.entities.outbox_message import OutboxMessage
from app.domain.repositories.account_repo import AccountRepository
from app.domain.repositories.actor_action_repo import ActorActionRepository
from app.domain.repositories.economic_action_repo import EconomicActionRepository
from app.domain.repositories.ledger_repo import LedgerRepository
from app.domain.repositories.outbox_repo import OutboxRepository
from app.domain.repositories.processed_event_repo import ProcessedEventRepository
from app.domain.repositories.reward_batch_repo import RewardBatchRepository
from app.domain.services.reward_engine import RewardEngine
from app.infrastructure.db.transaction import transaction
from app.infrastructure.rabbitmq.consumer import RewardEvent
from app.infrastructure.redis.cache import CacheService

logger = get_logger(__name__)


class ProcessRewardEventUseCase:
    """Processes a single reward event from RabbitMQ."""

    def __init__(
        self,
        pool: Pool,
        account_repo: AccountRepository,
        ledger_repo: LedgerRepository,
        actor_action_repo: ActorActionRepository,
        economic_action_repo: EconomicActionRepository,
        reward_batch_repo: RewardBatchRepository,
        processed_event_repo: ProcessedEventRepository,
        outbox_repo: OutboxRepository,
        cache: CacheService | None = None,
    ) -> None:
        self._pool = pool
        self._account_repo = account_repo
        self._ledger_repo = ledger_repo
        self._actor_action_repo = actor_action_repo
        self._economic_action_repo = economic_action_repo
        self._reward_batch_repo = reward_batch_repo
        self._processed_event_repo = processed_event_repo
        self._outbox_repo = outbox_repo
        self._cache = cache

    async def execute(self, event: RewardEvent) -> None:
        # ── 1. Quick Redis idempotency check ─────────────
        if self._cache:
            if await self._cache.is_event_processed(event.event_id):
                logger.info(
                    "event_already_processed_cache", event_id=str(event.event_id)
                )
                return

        async with transaction(self._pool) as conn:
            # ── 2. DB idempotency check ──────────────────
            if await self._processed_event_repo.exists(event.event_id, conn):
                logger.info("event_already_processed_db", event_id=str(event.event_id))
                return

            # ── 3. Fetch active economic version ─────────
            config = await self._economic_action_repo.get_active_version(
                event.action_code, conn
            )
            if config is None:
                logger.warning(
                    "no_active_economic_config",
                    action_code=event.action_code,
                    event_id=str(event.event_id),
                )
                # Still mark as processed to avoid infinite retries
                await self._processed_event_repo.mark_processed(
                    event.event_id, event.action_code, conn
                )
                return

            # ── 4. Get or create actor account ───────────
            actor_account = await self._account_repo.get_or_create_by_user_id(
                event.actor_id, conn
            )

            # ── 5. Calculate rewards ─────────────────────
            calc = RewardEngine.calculate(
                actor_id=event.actor_id,
                content_id=event.content_id,
                action_code=event.action_code,
                config=config,
                actor_account_id=actor_account.id,
            )

            # ── 6. Persist actor_action ──────────────────
            await self._actor_action_repo.create(calc.actor_action, conn)

            # ── 7. Actor ledger entry + balance update ───
            if calc.actor_ledger_entry is not None:
                await self._ledger_repo.append(calc.actor_ledger_entry, conn)
                actor_account.credit(config.actor_reward)
                await self._account_repo.update_balance(
                    actor_account.id, actor_account.balance, conn
                )
                # Invalidate cached balance
                if self._cache:
                    await self._cache.invalidate_balance(actor_account.id)

            # ── 8. Accumulate publisher reward batch ─────
            await self._reward_batch_repo.upsert_batch(
                content_id=event.content_id,
                publisher_id=event.publisher_id,
                action_code=event.action_code,
                publisher_reward=calc.publisher_reward,
                platform_fee=calc.platform_fee,
                treasury_cut=calc.treasury_cut,
                conn=conn,
            )

            # ── 9. Write outbox message (same transaction) ──
            outbox_msg = OutboxMessage.create(
                aggregate_type="reward_event",
                aggregate_id=event.event_id,
                event_type=f"reward.{event.action_code}.processed",
                payload={
                    "event_id": str(event.event_id),
                    "actor_id": str(event.actor_id),
                    "publisher_id": str(event.publisher_id),
                    "content_id": str(event.content_id),
                    "action_code": event.action_code,
                    "actor_reward": config.actor_reward,
                    "publisher_reward": config.publisher_reward,
                },
            )
            await self._outbox_repo.insert(outbox_msg, conn)

            # ── 10. Mark event processed (DB) ────────────
            await self._processed_event_repo.mark_processed(
                event.event_id, event.action_code, conn
            )

        # ── 11. Mark event processed (Redis, outside tx) ─
        if self._cache:
            await self._cache.mark_event_processed(event.event_id)

        logger.info(
            "reward_event_processed",
            event_id=str(event.event_id),
            action_code=event.action_code,
            actor_reward=config.actor_reward,
            publisher_reward=config.publisher_reward,
        )
