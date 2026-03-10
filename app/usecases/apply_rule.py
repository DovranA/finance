"""Rule engine use case — evaluates DB-stored rules for incoming events."""

from __future__ import annotations

import uuid

from asyncpg import Pool

from app.core.logging import get_logger
from app.domain.entities.idempotency_key import Transaction
from app.domain.entities.ledger_entry import LedgerEntry
from app.domain.exceptions import AccountNotFound
from app.domain.policies.engine import ConditionEngine
from app.domain.repositories.account_repo import AccountRepository
from app.domain.repositories.ledger_repo import LedgerRepository
from app.domain.repositories.rule_repo import RuleRepository
from app.domain.repositories.transfer_repo import TransactionRepository
from app.domain.value_objects.enums import AccountTypes, LedgerDirection
from app.infrastructure.db.transaction import transaction
from app.infrastructure.redis.cache import CacheService

logger = get_logger(__name__)


class ApplyRuleUseCase:
    """Look up active rules for an event_code, validate conditions, execute actions."""

    def __init__(
        self,
        pool: Pool,
        rule_repo: RuleRepository,
        account_repo: AccountRepository,
        transaction_repo: TransactionRepository,
        ledger_repo: LedgerRepository,
        condition_engine: ConditionEngine,
        cache: CacheService | None = None,
    ) -> None:
        self._pool = pool
        self._rule_repo = rule_repo
        self._account_repo = account_repo
        self._transaction_repo = transaction_repo
        self._ledger_repo = ledger_repo
        self._condition_engine = condition_engine
        self._cache = cache

    async def execute(
        self,
        *,
        event_code: str,
        account_id: uuid.UUID,
        idempotency_key: str,
        metadata: dict | None = None,
    ) -> list[dict]:
        """Apply all matching rules for the given event_code.

        Returns a list of action results (one per matched rule).
        """
        metadata = metadata or {}
        metadata["event_code"] = event_code
        results: list[dict] = []

        async with transaction(self._pool) as conn:
            rules = await self._rule_repo.get_active_by_event_code(event_code, conn)
            if not rules:
                logger.info("no_active_rules", event_code=event_code)
                return results
            account = await self._account_repo.get_for_update(account_id, conn)
            if account is None:
                raise AccountNotFound(f"Account {account_id} not found")
            account.ensure_active()
            treasury = await self._account_repo.get_by_account_type(
                AccountTypes.TREASURY, conn
            )
            for rule in rules:
                # Validate conditions
                await self._condition_engine.validate(
                    rule.conditions,
                    account=account,
                    metadata=metadata,
                    conn=conn,
                )
                print("Done validation")
                actions = rule.actions
                direction = LedgerDirection(actions.get("direction", 1))
                amount = actions.get("reward", actions.get("amount", 0))
                print(f"Action is {actions}")
                print(f"Direction is {direction}")
                print(f"Amount is {amount}")
                if amount <= 0:
                    continue
                print("Amount enough")
                # Create transaction record
                rule_idem_key = f"{idempotency_key}:{rule.id}"
                existing = await self._transaction_repo.get_by_key(rule_idem_key, conn)
                if existing and existing.status == "completed":
                    logger.info(
                        "rule_already_applied",
                        rule_id=str(rule.id),
                        idempotency_key=rule_idem_key,
                    )
                    continue

                tx = Transaction.create(
                    idempotency_key=rule_idem_key,
                    reference_type=event_code,
                    reference_id=str(account_id),
                    metadata={
                        "rule_id": str(rule.id),
                        "event_code": event_code,
                        **(metadata or {}),
                    },
                )
                await self._transaction_repo.save(tx, conn)

                if direction == LedgerDirection.DIRECTION_CREDIT:
                    # Credit the user, debit treasury
                    await self._account_repo.credit(account_id, amount, conn)
                    await self._ledger_repo.insert(
                        LedgerEntry.create(
                            account_id=account_id,
                            transaction_id=tx.id,
                            amount=amount,
                            direction=LedgerDirection.DIRECTION_CREDIT,
                        ),
                        conn,
                    )
                    if treasury:
                        await self._account_repo.debit(treasury.id, amount, conn)
                        await self._ledger_repo.insert(
                            LedgerEntry.create(
                                account_id=treasury.id,
                                transaction_id=tx.id,
                                amount=amount,
                                direction=LedgerDirection.DIRECTION_DEBIT,
                            ),
                            conn,
                        )
                else:
                    # Debit the user, credit treasury
                    await self._account_repo.debit(account_id, amount, conn)
                    await self._ledger_repo.insert(
                        LedgerEntry.create(
                            account_id=account_id,
                            transaction_id=tx.id,
                            amount=amount,
                            direction=LedgerDirection.DIRECTION_DEBIT,
                        ),
                        conn,
                    )
                    if treasury:
                        await self._account_repo.credit(treasury.id, amount, conn)
                        await self._ledger_repo.insert(
                            LedgerEntry.create(
                                account_id=treasury.id,
                                transaction_id=tx.id,
                                amount=amount,
                                direction=LedgerDirection.DIRECTION_CREDIT,
                            ),
                            conn,
                        )

                await self._transaction_repo.mark_completed(rule_idem_key, conn)

                results.append(
                    {
                        "rule_id": str(rule.id),
                        "event_code": event_code,
                        "direction": int(direction),
                        "amount": amount,
                        "currency": actions.get("currency", "TMT"),
                        "status": "applied",
                    }
                )

            # Invalidate cache
            if self._cache:
                await self._cache.invalidate_balance(account_id)
                if treasury:
                    await self._cache.invalidate_balance(treasury.id)

        return results
