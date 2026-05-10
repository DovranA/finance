"""Rule engine use case — evaluates DB-stored rules for incoming events."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from asyncpg import Connection, Pool
from asyncpg.exceptions import UniqueViolationError

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
from app.domain.repositories.user_gateway import UserGateway
from app.domain.value_objects.enums import AccountTypes, LedgerDirection
from app.infrastructure.db.transaction import transaction
from app.infrastructure.redis.cache import CacheService
from app.infrastructure.rest.client import RestApiError

logger = get_logger(__name__)


def _ensure_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


class ApplyRuleUseCase:
    """Look up active rules for an event_code, validate conditions, execute actions."""

    def __init__(
        self,
        pool: Pool,
        rule_repo: RuleRepository,
        account_repo: AccountRepository,
        transaction_repo: TransactionRepository,
        ledger_repo: LedgerRepository,
        user_gateway: UserGateway,
        condition_engine: ConditionEngine,
        cache: CacheService | None = None,
    ) -> None:
        self._pool = pool
        self._rule_repo = rule_repo
        self._account_repo = account_repo
        self._transaction_repo = transaction_repo
        self._ledger_repo = ledger_repo
        self._user_gateway = user_gateway
        self._condition_engine = condition_engine
        self._cache = cache

    # ── Public entry point ───────────────────────────────

    async def execute(
        self,
        *,
        rule_id: uuid.UUID | None = None,
        event_code: str | None = None,
        user_id: uuid.UUID,
        metadata: dict | None = None,
    ) -> dict | None:

        metadata = metadata or {}
        try:
            approval_action = str(metadata.get("approval_action") or "").strip().lower()
            if approval_action in {"approve", "reject"}:
                async with transaction(self._pool) as conn:
                    return await self._handle_official_approval_action(
                        action=approval_action,
                        requested_user_id=user_id,
                        metadata=metadata,
                        conn=conn,
                    )

            async with transaction(self._pool) as conn:
                rule = await self._fetch_rule(
                    rule_id=rule_id, event_code=event_code, conn=conn
                )
                if not rule:
                    logger.info(
                        "no_active_rules",
                        event_code=event_code,
                        rule_id=str(rule_id) if rule_id else None,
                    )
                    return None

                event_code = event_code or rule.event_code
                metadata["event_code"] = event_code

                rule_currency = (rule.actions or {}).get("currency", "TOKEN")

                if self._should_lookup_role(rule, metadata):
                    await self._inject_user_role(
                        current_user_id=user_id,
                        target_user_id=user_id,
                        metadata=metadata,
                    )

                account = await self._get_or_create_account_for_update(
                    user_id, conn, currency=rule_currency
                )
                account.ensure_active()

                treasury = await self._account_repo.get_by_account_type(
                    AccountTypes.TREASURY,
                    conn,
                    rule_currency,
                )

                result = await self._apply_single_rule(
                    rule=rule,
                    account=account,
                    treasury=treasury,
                    event_code=event_code,
                    user_id=user_id,
                    metadata=metadata,
                    conn=conn,
                )

                await self._invalidate_caches(account.id, treasury)
        except ValueError as e:
            raise DomainError(e)
        return result

    async def execute_batch(
        self,
        *,
        event_code: str,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        touched_accounts: set[uuid.UUID] = set()

        pending_txs: list[Transaction] = []
        pending_entries: list[LedgerEntry] = []
        pending_effects: list[dict[str, Any]] = []
        pending_redis_updates: list[tuple] = (
            []
        )  # (rule, account_id, idem_key, event_code)

        async with transaction(self._pool) as conn:
            rule = await self._fetch_rules(event_code, conn)
            if not rule:
                logger.info("no_active_rules", event_code=event_code)
                return {
                    "event_code": event_code,
                    "total": len(items),
                    "applied": 0,
                    "failed": len(items),
                    "results": [
                        {
                            "inbox_id": i.get("inbox_id"),
                            "user_id": str(i.get("user_id", "")),
                            "applied": False,
                            "applied_rule": None,
                            "error": "no_active_rules",
                        }
                        for i in items
                    ],
                }

            rule_currency = (rule.actions or {}).get("currency", "TOKEN")
            treasury = await self._account_repo.get_by_account_type(
                AccountTypes.TREASURY,
                conn,
                rule_currency,
            )

            accounts_cache: dict[uuid.UUID, Account] = {}

            for item in items:
                inbox_id = item.get("inbox_id")
                raw_metadata = item.get("metadata")
                if isinstance(raw_metadata, str):
                    try:
                        parsed_metadata = json.loads(raw_metadata)
                    except json.JSONDecodeError:
                        parsed_metadata = {}
                elif isinstance(raw_metadata, dict):
                    parsed_metadata = raw_metadata
                else:
                    parsed_metadata = {}

                metadata = dict(parsed_metadata)
                role = item.get("role")
                event_id = item.get("event_id")
                source_user_id = item.get("user_id")

                if role:
                    metadata["role"] = role
                if event_id:
                    metadata["event_id"] = str(event_id)
                metadata["event_code"] = event_code

                # Use savepoint for each item so database errors don't abort the entire transaction
                item_sp = conn.transaction()
                try:
                    await item_sp.start()
                    targets = self._resolve_target_users(rule, item)

                    if self._should_lookup_role(rule, metadata):
                        source_user_id_uuid = self._parse_uuid(source_user_id)
                        if source_user_id_uuid is None:
                            source_user_id_uuid = targets[0][1]
                        # await self._inject_user_roles_batch(
                        #     current_user_id=source_user_id_uuid,
                        #     target_user_ids=[target_id for _, target_id in targets],
                        #     metadata=metadata,
                        # )

                    any_applied = False
                    first_applied_rule: dict[str, Any] | None = None
                    errors: list[str] = []
                    candidate_tx_ids: list[uuid.UUID] = []
                    item_pending_txs: list[Transaction] = []
                    item_pending_effects: list[dict[str, Any]] = []
                    item_touched_accounts: set[uuid.UUID] = set()
                    item_pending_redis_updates: list[tuple] = []
                    item_cache_updates: list[tuple[uuid.UUID, Account]] = []

                    for target_key, user_id in targets:
                        per_target_metadata = dict(metadata)
                        per_target_metadata["target_key"] = target_key

                        amount_override = None
                        target_amounts = (rule.actions or {}).get(
                            "target_amounts"
                        ) or {}
                        if isinstance(target_amounts, dict):
                            amount_override = target_amounts.get(target_key)

                        if user_id in accounts_cache:
                            account = accounts_cache[user_id]
                        else:
                            account = await self._get_or_create_account_for_update(
                                user_id,
                                conn,
                                currency=rule_currency,
                            )
                            item_cache_updates.append((user_id, account))

                        account.ensure_active()

                        calc_res = await self._calculate_rule_application(
                            rule=rule,
                            account=account,
                            treasury=treasury,
                            event_code=event_code,
                            user_id=user_id,
                            metadata=per_target_metadata,
                            amount_override=amount_override,
                            conn=conn,
                        )

                        if calc_res and calc_res.get("status") == "applied":
                            tx = calc_res["tx"]
                            entries = calc_res["entries"]
                            amount = calc_res["amount"]
                            direction = calc_res["direction"]
                            item_pending_txs.append(tx)
                            candidate_tx_ids.append(tx.id)
                            item_pending_effects.append(
                                {
                                    "tx_id": tx.id,
                                    "idempotency_key": calc_res["idem_key"],
                                    "account": account,
                                    "amount": amount,
                                    "direction": direction,
                                    "entries": entries,
                                    "rule": rule,
                                    "event_code": event_code,
                                }
                            )

                            any_applied = True
                            if first_applied_rule is None:
                                first_applied_rule = {
                                    "rule_id": str(rule.id),
                                    "event_code": event_code,
                                    "direction": int(direction),
                                    "amount": amount,
                                    "currency": calc_res.get("currency", "TOKEN"),
                                    "status": "applied",
                                    "target_user_id": str(user_id),
                                    "target_key": target_key,
                                }
                        else:
                            err = calc_res.get("unsuccess") if calc_res else None
                            if err:
                                errors.append(err)

                    results.append(
                        {
                            "inbox_id": inbox_id,
                            "user_id": str(source_user_id),
                            "applied": any_applied,
                            "applied_rule": first_applied_rule,
                            "error": "; ".join(errors) if errors else None,
                            "_candidate_tx_ids": [
                                str(tx_id) for tx_id in candidate_tx_ids
                            ],
                        }
                    )
                    await item_sp.commit()
                    pending_txs.extend(item_pending_txs)
                    pending_effects.extend(item_pending_effects)
                    for user_id, account in item_cache_updates:
                        accounts_cache[user_id] = account
                except Exception as exc:
                    await item_sp.rollback()
                    results.append(
                        {
                            "inbox_id": inbox_id,
                            "user_id": str(source_user_id),
                            "applied": False,
                            "applied_rule": None,
                            "error": str(exc),
                        }
                    )

            tx_id_to_idem = {tx.id: tx.idempotency_key for tx in pending_txs}
            inserted_tx_ids: set[uuid.UUID] = set()
            if pending_txs:
                inserted_tx_ids = set(
                    await self._transaction_repo.save_many(pending_txs, conn)
                )

            for effect in pending_effects:
                if effect["tx_id"] not in inserted_tx_ids:
                    continue

                account = effect["account"]
                amount = effect["amount"]
                direction = effect["direction"]
                if direction == LedgerDirection.DIRECTION_CREDIT:
                    account.credit(amount)
                else:
                    account.debit(amount)

                pending_entries.extend(effect["entries"])
                touched_accounts.add(account.id)
                pending_redis_updates.append(
                    (
                        effect["rule"],
                        account.id,
                        effect["idempotency_key"],
                        effect["event_code"],
                    )
                )

            if pending_entries:
                await self._ledger_repo.insert_many(pending_entries, conn)

            inserted_tx_id_strings = {str(tx_id) for tx_id in inserted_tx_ids}
            duplicate_item_count = 0
            duplicate_key_count = 0
            for result in results:
                candidate_ids = [
                    tx_id
                    for tx_id in result.pop("_candidate_tx_ids", [])
                    if isinstance(tx_id, str)
                ]
                if not candidate_ids:
                    continue

                inserted_for_item = [
                    tx_id for tx_id in candidate_ids if tx_id in inserted_tx_id_strings
                ]
                skipped_for_item = [
                    tx_id
                    for tx_id in candidate_ids
                    if tx_id not in inserted_tx_id_strings
                ]

                result["applied"] = bool(inserted_for_item)
                if not inserted_for_item:
                    result["applied_rule"] = None

                if skipped_for_item:
                    skipped_keys = [
                        tx_id_to_idem[uuid.UUID(tx_id)]
                        for tx_id in skipped_for_item
                        if uuid.UUID(tx_id) in tx_id_to_idem
                    ]
                    duplicate_reason = (
                        "duplicate idempotency_key skipped"
                        if skipped_keys
                        else "duplicate transaction skipped"
                    )
                    result["error"] = (
                        f"{result['error']}; {duplicate_reason}"
                        if result.get("error")
                        else duplicate_reason
                    )
                    duplicate_item_count += 1
                    duplicate_key_count += len(skipped_for_item)

                    if not inserted_for_item:
                        result["skipped_duplicate"] = True

            if duplicate_item_count:
                logger.info(
                    "batch_duplicates_skipped",
                    event_code=event_code,
                    duplicate_items=duplicate_item_count,
                    duplicate_keys=duplicate_key_count,
                )

            for acc in accounts_cache.values():
                if acc.id in touched_accounts:
                    await self._account_repo.update_balance(acc.id, acc.balance, conn)

            if self._cache:
                for r, acc_id, k, ec in pending_redis_updates:
                    await self._mark_one_time(r, acc_id, k)
                    await self._incr_daily_count(r, acc_id, ec)

                for account_id in touched_accounts:
                    await self._cache.invalidate_balance(account_id)
                if treasury and touched_accounts:
                    await self._cache.invalidate_balance(treasury.id)

        applied_count = sum(1 for r in results if r["applied"])
        skipped_count = sum(1 for r in results if r.get("skipped_duplicate"))
        return {
            "event_code": event_code,
            "total": len(results),
            "applied": applied_count,
            "skipped": skipped_count,
            "failed": len(results) - applied_count - skipped_count,
            "results": results,
        }

    async def can_apply(
        self,
        *,
        rule_id: uuid.UUID | None = None,
        event_code: str | None = None,
        user_id: uuid.UUID,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Validate whether a rule can be applied without mutating balances/transactions."""
        metadata = metadata or {}

        async with self._pool.acquire() as conn:
            rule = await self._fetch_rule(
                rule_id=rule_id, event_code=event_code, conn=conn
            )
            if not rule:
                return {
                    "can_apply": False,
                    "reason": "no_active_rules",
                    "rule_id": str(rule_id) if rule_id else None,
                    "event_code": event_code,
                }
            event_code = event_code or rule.event_code
            metadata["event_code"] = event_code

            if self._should_lookup_role(rule, metadata):
                await self._inject_user_role(
                    current_user_id=user_id,
                    target_user_id=user_id,
                    metadata=metadata,
                )

            account_currency = (rule.actions or {}).get("currency", "TOKEN")
            account = await self._account_repo.get_by_owner_id(
                user_id,
                conn,
                currency=account_currency,
            )
            if account is None:
                account = Account.create(
                    user_id=user_id,
                    currency=account_currency,
                    owner_type="user",
                    balance=0,
                )

            account.ensure_active()

            rule_idem_key = self._resolve_idem_key(
                rule, event_code, user_id, account.id, uuid.uuid4().hex, metadata
            )
            metadata["idempotency_key"] = rule_idem_key

            try:
                await self._condition_engine.validate(
                    rule.conditions, account=account, metadata=metadata, conn=conn
                )
            except Exception as exc:

                return {
                    "can_apply": False,
                    "reason": str(exc),
                    "rule_id": str(rule.id),
                    "event_code": rule.event_code,
                }

            actions = rule.actions or {}
            amount = actions.get("amount", 0)
            if amount <= 0:
                target_amounts = actions.get("target_amounts") or {}
                if isinstance(target_amounts, dict):
                    target_key = str(metadata.get("target_key") or "user_id")
                    fallback_amount = target_amounts.get(target_key)
                    if fallback_amount is None:
                        fallback_amount = target_amounts.get("user_id")
                    try:
                        amount = int(fallback_amount or 0)
                    except (TypeError, ValueError):
                        amount = 0
            if amount <= 0:
                return {
                    "can_apply": False,
                    "reason": "amount_not_positive",
                    "rule_id": str(rule.id),
                    "event_code": rule.event_code,
                }

            if self._requires_admin_approval(rule, metadata):
                existing = await self._transaction_repo.get_by_key(rule_idem_key, conn)
                if existing is not None:
                    if existing.status == "pending":
                        return {
                            "can_apply": False,
                            "reason": "pending_approval",
                            "rule_id": str(rule.id),
                            "event_code": rule.event_code,
                            "amount": amount,
                            "currency": actions.get("currency", "TOKEN"),
                            "direction": actions.get("direction", 1),
                            "approval_required": True,
                        }
                    if existing.status == "completed":
                        return {
                            "can_apply": False,
                            "reason": "already_applied",
                            "rule_id": str(rule.id),
                            "event_code": rule.event_code,
                        }
                    return {
                        "can_apply": False,
                        "reason": "rejected",
                        "rule_id": str(rule.id),
                        "event_code": rule.event_code,
                    }

            if await self._is_already_applied(rule.id, rule_idem_key, conn):
                return {
                    "can_apply": False,
                    "reason": "already_applied",
                    "rule_id": str(rule.id),
                    "event_code": rule.event_code,
                }
            cooldown_days = rule.conditions.get("cooldown_days")
            possible = {
                "can_apply": True,
                "reason": None,
                "rule_id": str(rule.id),
                "event_code": rule.event_code,
                "amount": amount,
                "currency": actions.get("currency", "TOKEN"),
                "direction": actions.get("direction", 1),
            }
            if self._requires_admin_approval(rule, metadata):
                possible["approval_required"] = True
            if cooldown_days is not None:
                try:
                    days = int(cooldown_days)
                    if days > 0:
                        expired_at = (
                            datetime.now(timezone.utc) + timedelta(days=days)
                        ).isoformat()
                        possible["expired_at"] = expired_at
                except (TypeError, ValueError):
                    pass
            return possible

    # ── Rule fetching (cache → DB) ───────────────────────

    async def _fetch_rules(self, event_code: str, conn: Connection) -> Rule | None:
        return await self._fetch_rule(rule_id=None, event_code=event_code, conn=conn)

    async def _fetch_rule(
        self,
        *,
        rule_id: uuid.UUID | None,
        event_code: str | None,
        conn: Connection,
    ) -> Rule | None:
        if rule_id is not None:
            rule = await self._rule_repo.get_by_id(rule_id, conn)
            if rule is not None and rule.is_usable:
                return rule

        if not event_code:
            return None

        if self._cache:
            cached = await self._cache.get_cached_rules(event_code)
            if cached is not None:
                rules = self._deserialize_rules(cached)
                return rules[0] if rules else None

        rule = await self._rule_repo.get_active_by_event_code(event_code, conn)

        if self._cache and rule:
            await self._cache.set_cached_rules(
                event_code, self._serialize_rules([rule])
            )
        return rule

    @staticmethod
    def _deserialize_rules(raw: list[dict]) -> list[Rule]:
        rules = [
            Rule(
                id=uuid.UUID(r["id"]),
                event_code=r["event_code"],
                description_i18n=r.get("description_i18n"),
                conditions=_ensure_dict(r.get("conditions", {})),
                actions=_ensure_dict(r.get("actions", {})),
                tags=list(r.get("tags") or []),
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
                "description_i18n": r.description_i18n or {},
                "conditions": r.conditions,
                "actions": r.actions,
                "tags": r.tags,
                "priority": r.priority,
                "is_active": r.is_active,
                "expired_at": r.expired_at.isoformat() if r.expired_at else None,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in rules
        ]

    # ── Calculation without persistence (Batch) ───────────

    async def _calculate_rule_application(
        self,
        *,
        rule: Rule,
        account: Account,
        treasury: Account | None,
        event_code: str,
        user_id: uuid.UUID,
        metadata: dict,
        amount_override: int | None = None,
        conn: Connection,
    ) -> dict | None:
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
        amount = (
            amount_override if amount_override is not None else actions.get("amount", 0)
        )

        # Apply view_percentage multiplier if available
        multiplier = metadata.get("view_percentage_multiplier")
        if multiplier is not None and amount > 0:
            amount = int(amount * float(multiplier))
        if amount <= 0:
            return None

        if await self._is_already_applied(rule.id, rule_idem_key, conn):
            return None

        tx = Transaction.create(
            idempotency_key=rule_idem_key,
            reference_type=event_code,
            reference_id=str(account.id),
            metadata={"rule_id": str(rule.id), "event_code": event_code, **metadata},
            status="completed",
        )

        entries = []
        opposite = (
            LedgerDirection.DIRECTION_DEBIT
            if direction == LedgerDirection.DIRECTION_CREDIT
            else LedgerDirection.DIRECTION_CREDIT
        )

        entries.append(
            LedgerEntry.create(
                account_id=account.id,
                transaction_id=tx.id,
                amount=amount,
                direction=direction,
            )
        )

        if treasury:
            entries.append(
                LedgerEntry.create(
                    account_id=treasury.id,
                    transaction_id=tx.id,
                    amount=amount,
                    direction=opposite,
                )
            )

        return {
            "tx": tx,
            "entries": entries,
            "amount": amount,
            "direction": direction,
            "idem_key": rule_idem_key,
            "status": "applied",
            "currency": actions.get("currency", "TOKEN"),
        }

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

        await self._condition_engine.validate(
            rule.conditions, account=account, metadata=metadata, conn=conn
        )

        actions = rule.actions
        direction = LedgerDirection(actions.get("direction", 1))
        amount = actions.get("amount", 0)

        if amount <= 0:
            # Support single-event rules that define per-target amounts
            # (e.g. target_amounts.user_id) without requiring batch path.
            target_amounts = actions.get("target_amounts") or {}
            if isinstance(target_amounts, dict):
                target_key = str(metadata.get("target_key") or "user_id")
                fallback_amount = target_amounts.get(target_key)
                if fallback_amount is None:
                    fallback_amount = target_amounts.get("user_id")
                try:
                    amount = int(fallback_amount or 0)
                except (TypeError, ValueError):
                    amount = 0

        # Apply view_percentage multiplier if available
        multiplier = metadata.get("view_percentage_multiplier")
        if multiplier is not None and amount > 0:
            amount = int(amount * float(multiplier))
        dynamic_amount = metadata.get("dynamic_amount")
        if dynamic_amount is not None and dynamic_amount > 0:
            amount = int(dynamic_amount)
        if amount <= 0:
            return None

        if self._requires_admin_approval(rule, metadata):
            existing = await self._transaction_repo.get_by_key(rule_idem_key, conn)
            if existing is not None:
                if existing.status == "failed":
                    return None
                return self._official_request_result(
                    rule=rule,
                    amount=amount,
                    direction=direction,
                    transaction=existing,
                    status=(
                        "applied"
                        if existing.status == "completed"
                        else "pending_approval"
                    ),
                )

            is_debit_direction = direction == LedgerDirection.DIRECTION_DEBIT
            tx = Transaction.create(
                idempotency_key=rule_idem_key,
                reference_type=event_code,
                reference_id=str(account.id),
                metadata={
                    "rule_id": str(rule.id),
                    "event_code": event_code,
                    "request_type": "official_approval",
                    "approval_required": True,
                    "user_id": str(user_id),
                    "account_id": str(account.id),
                    "amount": amount,
                    "currency": actions.get("currency", "TOKEN"),
                    "direction": int(direction),
                    "funds_reserved": is_debit_direction,
                    **metadata,
                },
                status="pending",
            )
            await self._transaction_repo.save(tx, conn)

            if is_debit_direction:
                # Reserve user funds immediately; approve/reject decides final settlement.
                await self._account_repo.debit(account.id, amount, conn)
                await self._ledger_repo.insert(
                    LedgerEntry.create(
                        account_id=account.id,
                        transaction_id=tx.id,
                        amount=amount,
                        direction=LedgerDirection.DIRECTION_DEBIT,
                    ),
                    conn,
                )

            return self._official_request_result(
                rule=rule,
                amount=amount,
                direction=direction,
                transaction=tx,
                status="pending_approval",
            )

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
        result = {
            "rule_id": str(rule.id),
            "event_code": rule.event_code,
            "direction": int(direction),
            "amount": amount,
            "currency": actions.get("currency", "TOKEN"),
            "status": "applied",
        }
        cooldown_days = rule.conditions.get("cooldown_days")
        if cooldown_days is not None:
            try:
                days = int(cooldown_days)
                if days > 0:
                    expired_at = (
                        datetime.now(timezone.utc) + timedelta(days=days)
                    ).isoformat()
                    result["expired_at"] = expired_at
            except (TypeError, ValueError):

                pass

        return result

    @staticmethod
    def _requires_admin_approval(rule: Rule, metadata: dict[str, Any]) -> bool:
        actions = rule.actions or {}
        if metadata.get("requires_approval") is True:
            return True
        return actions.get("requires_approval") is True

    @staticmethod
    def _official_request_result(
        *,
        rule: Rule,
        amount: int,
        direction: LedgerDirection,
        transaction: Transaction,
        status: str,
    ) -> dict[str, Any]:
        actions = rule.actions or {}
        return {
            "rule_id": str(rule.id),
            "event_code": rule.event_code,
            "direction": int(direction),
            "amount": amount,
            "currency": actions.get("currency", "TOKEN"),
            "status": status,
            "request_id": str(transaction.id),
            "idempotency_key": transaction.idempotency_key,
            "approval_required": True,
        }

    async def _handle_official_approval_action(
        self,
        *,
        action: str,
        requested_user_id: uuid.UUID,
        metadata: dict[str, Any],
        conn: Connection,
    ) -> dict[str, Any]:
        request_id_raw = metadata.get("request_id")
        request_id = self._parse_uuid(request_id_raw)
        if request_id is None:
            raise DomainError("request_id is required for approval_action")

        tx = await self._transaction_repo.get_by_id(request_id, conn)
        if tx is None:
            raise DomainError("official request not found")

        tx_meta = tx.metadata or {}
        if not tx_meta.get("approval_required"):
            raise DomainError("transaction is not an approval request")

        tx_user_id = self._parse_uuid(tx_meta.get("user_id"))
        if tx_user_id is None:
            raise DomainError("invalid approval request payload")
        if tx_user_id != requested_user_id:
            raise DomainError("user_id does not match request owner")

        currency = str(tx_meta.get("currency") or "TOKEN")
        amount = int(tx_meta.get("amount") or 0)
        if amount <= 0:
            raise DomainError("official request amount must be positive")

        direction_value = int(
            tx_meta.get("direction") or LedgerDirection.DIRECTION_DEBIT
        )
        direction = LedgerDirection(direction_value)
        funds_reserved = bool(tx_meta.get("funds_reserved"))

        if tx.status == "completed":
            if action == "approve":
                return self._official_approval_action_result(tx, "approved")
            raise DomainError("official request already approved")

        if tx.status == "failed":
            if action == "reject":
                return self._official_approval_action_result(tx, "rejected")
            raise DomainError("official request already rejected")

        if action == "reject":
            if funds_reserved and direction == LedgerDirection.DIRECTION_DEBIT:
                account_id = self._parse_uuid(tx_meta.get("account_id"))
                if account_id is None:
                    raise DomainError("invalid approval request account")

                account = await self._account_repo.get_for_update(account_id, conn)
                if account is None:
                    raise AccountNotFound(f"Account {account_id} not found")

                await self._account_repo.credit(account.id, amount, conn)
                await self._ledger_repo.insert(
                    LedgerEntry.create(
                        account_id=account.id,
                        transaction_id=tx.id,
                        amount=amount,
                        direction=LedgerDirection.DIRECTION_CREDIT,
                    ),
                    conn,
                )

            await self._transaction_repo.mark_failed(tx.idempotency_key, conn)
            return self._official_approval_action_result(tx, "rejected")

        treasury = await self._account_repo.get_by_account_type(
            AccountTypes.TREASURY,
            conn,
            currency,
        )
        if treasury is None:
            raise AccountNotFound(
                f"Treasury account not found for currency '{currency}'"
            )

        if direction == LedgerDirection.DIRECTION_DEBIT:
            if not funds_reserved:
                account = await self._account_repo.get_by_owner_id_for_update(
                    tx_user_id,
                    conn,
                    currency=currency,
                )
                if account is None:
                    raise AccountNotFound(
                        f"Account {tx_user_id} ({currency}) not found"
                    )
                account.ensure_active()

                await self._account_repo.debit(account.id, amount, conn)
                await self._ledger_repo.insert(
                    LedgerEntry.create(
                        account_id=account.id,
                        transaction_id=tx.id,
                        amount=amount,
                        direction=LedgerDirection.DIRECTION_DEBIT,
                    ),
                    conn,
                )

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

        await self._transaction_repo.mark_completed(tx.idempotency_key, conn)
        return self._official_approval_action_result(tx, "approved")

    @staticmethod
    def _official_approval_action_result(
        tx: Transaction, status: str
    ) -> dict[str, Any]:
        metadata = tx.metadata or {}
        return {
            "request_id": str(tx.id),
            "idempotency_key": tx.idempotency_key,
            "status": status,
            "user_id": metadata.get("user_id"),
            "amount": metadata.get("amount"),
            "currency": metadata.get("currency", "TOKEN"),
            "event_code": metadata.get("event_code"),
            "approval_required": bool(metadata.get("approval_required")),
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
        one_time_only = rule.conditions.get("one_time_only")
        pattern = rule.conditions.get("idempotency_pattern")

        if pattern:
            context = {
                "event_code": event_code,
                "user_id": str(user_id),
                "account_id": str(account_id),
                "rule_id": str(rule.id),
                **metadata,
            }
            seed = resolve_idempotency_pattern(pattern, context)
        else:
            seed = fallback_key

        if not one_time_only:
            seed = f"{seed}:{datetime.now(timezone.utc).isoformat(timespec='microseconds')}"

        return generate_idempotency_key(seed, str(rule.id))

    @staticmethod
    def _resolve_target_users(
        rule: Rule, item: dict[str, Any]
    ) -> list[tuple[str, uuid.UUID]]:
        actions = rule.actions or {}
        metadata = _ensure_dict(item.get("metadata"))
        target_keys = actions.get("target_users") or ["user_id"]

        resolved: list[tuple[str, uuid.UUID]] = []

        for key in target_keys:
            raw_val = None
            if key == "user_id":
                raw_val = item.get("user_id")
            elif key in item:
                raw_val = item.get(key)
            elif key in metadata:
                raw_val = metadata.get(key)
            elif isinstance(key, str) and key.startswith("metadata."):
                raw_val = metadata.get(key.split(".", 1)[1])

            if raw_val is None:
                continue

            try:
                target_id = uuid.UUID(str(raw_val))
            except (ValueError, TypeError):
                continue

            pair = (str(key), target_id)
            if pair not in resolved:
                resolved.append(pair)

        if resolved:
            return resolved
        return [("user_id", uuid.UUID(str(item["user_id"])))]

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

    async def _get_or_create_account_for_update(
        self,
        user_id: uuid.UUID,
        conn: Connection,
        currency: str = "TOKEN",
    ) -> Account:
        account = await self._account_repo.get_by_owner_id_for_update(
            user_id,
            conn,
            currency=currency,
        )
        if account is not None:
            return account

        existing_accounts = await self._account_repo.list_by_owner_id(user_id, conn)
        existing_account = next(
            (
                item
                for item in existing_accounts
                if item.currency.upper() == currency.upper()
            ),
            None,
        )
        if existing_account is not None:
            return existing_account

        try:
            await self._account_repo.create(
                Account.create(user_id=user_id, owner_type="user", currency=currency),
                conn,
            )
        except UniqueViolationError:
            # Another transaction created the account between read and insert.
            pass

        account = await self._account_repo.get_by_owner_id_for_update(
            user_id,
            conn,
            currency=currency,
        )
        if account is None:
            raise AccountNotFound(f"Account {user_id} ({currency}) not found")
        return account

    @staticmethod
    def _should_lookup_role(rule: Rule, metadata: dict[str, Any]) -> bool:
        return bool(rule.conditions.get("role_required")) and not metadata.get("role")

    @staticmethod
    def _parse_uuid(value: Any) -> uuid.UUID | None:
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError):
            return None

    async def _inject_user_role(
        self,
        *,
        current_user_id: uuid.UUID,
        target_user_id: uuid.UUID,
        metadata: dict[str, Any],
    ) -> None:
        try:
            users = await self._user_gateway.list_users_by_ids(
                current_user_id=current_user_id,
                user_ids=[target_user_id],
            )
        except RestApiError as exc:
            raise DomainError(f"user service lookup failed: {exc}") from exc

        for user in users:
            if user.id == target_user_id and user.role:
                metadata["role"] = user.role
                return

    async def _inject_user_roles_batch(
        self,
        *,
        current_user_id: uuid.UUID,
        target_user_ids: list[uuid.UUID],
        metadata: dict[str, Any],
    ) -> None:
        if metadata.get("role"):
            return

        deduped_ids = list(dict.fromkeys(target_user_ids))
        if not deduped_ids:
            return

        try:
            users = await self._user_gateway.list_users_by_ids(
                current_user_id=current_user_id,
                user_ids=deduped_ids,
            )
        except RestApiError as exc:
            raise DomainError(f"user service lookup failed: {exc}") from exc

        role_by_user = {user.id: user.role for user in users if user.role}
        for user_id in target_user_ids:
            role = role_by_user.get(user_id)
            if role:
                metadata["role"] = role
                return

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
