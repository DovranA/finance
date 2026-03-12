"""Rule engine use case — evaluates DB-stored rules for incoming events."""

from __future__ import annotations

import uuid
from datetime import datetime

from asyncpg import Connection, Pool

from app.core.logging import get_logger
from app.domain.entities.account import Account
from app.domain.entities.idempotency_key import (
    Transaction,
    generate_idempotency_key,
    resolve_idempotency_pattern,
)
from app.domain.entities.ledger_entry import LedgerEntry
from app.domain.entities.rule import Rule
from app.domain.exceptions import AccountNotFound, DomainError
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

    # ── Public entry point ───────────────────────────────

    async def execute(
        self,
        *,
        event_code: str,
        user_id: uuid.UUID,
        metadata: dict | None = None,
    ) -> list[dict]:
        metadata = metadata or {}
        metadata["event_code"] = event_code
        results: list[dict] = []
        try:
            async with transaction(self._pool) as conn:
                rules = await self._fetch_rules(event_code, conn)
                if not rules:
                    logger.info("no_active_rules", event_code=event_code)
                    return results

                account = await self._account_repo.get_by_owner_id_for_update(
                    user_id, conn
                )
                if account is None:
                    raise AccountNotFound(f"Account {user_id} not   found")
                account.ensure_active()

                treasury = await self._account_repo.get_by_account_type(
                    AccountTypes.TREASURY, conn
                )

                for rule in rules:
                    result = await self._apply_single_rule(
                        rule=rule,
                        account=account,
                        treasury=treasury,
                        event_code=event_code,
                        user_id=user_id,
                        metadata=metadata,
                        conn=conn,
                    )
                    print(rule.description)
                    print(result)
                    if result:
                        results.append(result)

                await self._invalidate_caches(account.id, treasury)
        except ValueError as e:
            raise DomainError(e)
        return results

    # ── Rule fetching (cache → DB) ───────────────────────

    async def _fetch_rules(self, event_code: str, conn: Connection) -> list[Rule]:
        if self._cache:
            cached = await self._cache.get_cached_rules(event_code)
            if cached is not None:
                return self._deserialize_rules(cached)

        rules = await self._rule_repo.get_active_by_event_code(event_code, conn)

        if self._cache and rules:
            await self._cache.set_cached_rules(event_code, self._serialize_rules(rules))
        return rules

    @staticmethod
    def _deserialize_rules(raw: list[dict]) -> list[Rule]:
        rules = [
            Rule(
                id=uuid.UUID(r["id"]),
                event_code=r["event_code"],
                description=r.get("description"),
                conditions=r.get("conditions", {}),
                actions=r.get("actions", {}),
                priority=r.get("priority", 0),
                is_active=r.get("is_active", True),
                expired_at=(
                    datetime.fromisoformat(r["expired_at"])
                    if r.get("expired_at")
                    else None
                ),
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
            )
            for r in raw
        ]
        return [r for r in rules if r.is_usable]

    @staticmethod
    def _serialize_rules(rules: list[Rule]) -> list[dict]:
        return [
            {
                "id": str(r.id),
                "event_code": r.event_code,
                "description": r.description,
                "conditions": r.conditions,
                "actions": r.actions,
                "priority": r.priority,
                "is_active": r.is_active,
                "expired_at": r.expired_at.isoformat() if r.expired_at else None,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in rules
        ]

    # ── Single rule application ──────────────────────────

    async def _apply_single_rule(
        self,
        *,
        rule: Rule,
        account: Account,
        treasury: Account | None,
        event_code: str,
        user_id: uuid.UUID,
        metadata: dict,
        conn: Connection,
    ) -> dict | None:
        # Resolve idempotency key BEFORE validation so one_time_only can use it
        rule_idem_key = self._resolve_idem_key(
            rule, event_code, user_id, account.id, uuid.uuid4().hex, metadata
        )
        metadata["idempotency_key"] = rule_idem_key

        try:
            await self._condition_engine.validate(
                rule.conditions, account=account, metadata=metadata, conn=conn
            )
        except ValueError as e:
            return {"unsuccess": f"Error on: {e}"}

        actions = rule.actions
        direction = LedgerDirection(actions.get("direction", 1))
        amount = actions.get("reward", actions.get("amount", 0))
        if amount <= 0:
            return None

        if await self._is_already_applied(rule.id, rule_idem_key, conn):
            return None

        tx = await self._create_transaction(
            rule_idem_key, event_code, account.id, rule.id, metadata, conn
        )

        await self._execute_ledger_transfer(
            account_id=account.id,
            treasury=treasury,
            tx_id=tx.id,
            amount=amount,
            direction=direction,
            conn=conn,
        )

        await self._transaction_repo.mark_completed(rule_idem_key, conn)
        await self._mark_one_time(rule, account.id, rule_idem_key)
        await self._incr_daily_count(rule, account.id, event_code)

        return {
            "rule_id": str(rule.id),
            "event_code": event_code,
            "direction": int(direction),
            "amount": amount,
            "currency": actions.get("currency", "TMT"),
            "status": "applied",
        }

    # ── Idempotency key resolution ───────────────────────

    @staticmethod
    def _resolve_idem_key(
        rule: Rule,
        event_code: str,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        fallback_key: str,
        metadata: dict,
    ) -> str:
        pattern = rule.conditions.get("idempotency_pattern")
        if pattern:
            context = {
                "event_code": event_code,
                "user_id": str(user_id),
                "account_id": str(account_id),
                "rule_id": str(rule.id),
                **metadata,
            }
            return resolve_idempotency_pattern(pattern, context)
        return generate_idempotency_key(fallback_key, str(rule.id))

    async def _is_already_applied(
        self, rule_id: uuid.UUID, idem_key: str, conn: Connection
    ) -> bool:
        existing = await self._transaction_repo.get_by_key(idem_key, conn)
        if existing and existing.status == "completed":
            logger.info(
                "rule_already_applied",
                rule_id=str(rule_id),
                idempotency_key=idem_key,
            )
            return True
        return False

    # ── Transaction creation ─────────────────────────────

    async def _create_transaction(
        self,
        idem_key: str,
        event_code: str,
        account_id: uuid.UUID,
        rule_id: uuid.UUID,
        metadata: dict,
        conn: Connection,
    ) -> Transaction:
        tx = Transaction.create(
            idempotency_key=idem_key,
            reference_type=event_code,
            reference_id=str(account_id),
            metadata={"rule_id": str(rule_id), "event_code": event_code, **metadata},
        )
        await self._transaction_repo.save(tx, conn)
        return tx

    # ── Ledger transfer (unified credit/debit) ───────────

    async def _execute_ledger_transfer(
        self,
        *,
        account_id: uuid.UUID,
        treasury: Account | None,
        tx_id: uuid.UUID,
        amount: int,
        direction: LedgerDirection,
        conn: Connection,
    ) -> None:
        opposite = (
            LedgerDirection.DIRECTION_DEBIT
            if direction == LedgerDirection.DIRECTION_CREDIT
            else LedgerDirection.DIRECTION_CREDIT
        )

        # Apply to user account
        await self._apply_entry(account_id, tx_id, amount, direction, conn)

        # Mirror on treasury
        if treasury:
            await self._apply_entry(treasury.id, tx_id, amount, opposite, conn)

    async def _apply_entry(
        self,
        account_id: uuid.UUID,
        tx_id: uuid.UUID,
        amount: int,
        direction: LedgerDirection,
        conn: Connection,
    ) -> None:
        if direction == LedgerDirection.DIRECTION_CREDIT:
            await self._account_repo.credit(account_id, amount, conn)
        else:
            await self._account_repo.debit(account_id, amount, conn)

        await self._ledger_repo.insert(
            LedgerEntry.create(
                account_id=account_id,
                transaction_id=tx_id,
                amount=amount,
                direction=direction,
            ),
            conn,
        )

    # ── Cache helpers ────────────────────────────────────

    async def _mark_one_time(
        self, rule: Rule, account_id: uuid.UUID, idem_key: str
    ) -> None:
        if self._cache and rule.conditions.get("one_time_only"):
            await self._cache.mark_one_time_done(account_id, idem_key)

    async def _incr_daily_count(
        self, rule: Rule, account_id: uuid.UUID, event_code: str
    ) -> None:
        if self._cache and rule.conditions.get("daily_limit"):
            await self._cache.incr_daily_count(account_id, event_code)

    async def _invalidate_caches(
        self, account_id: uuid.UUID, treasury: Account | None
    ) -> None:
        if self._cache:
            await self._cache.invalidate_balance(account_id)
            if treasury:
                await self._cache.invalidate_balance(treasury.id)
