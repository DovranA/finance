from __future__ import annotations

import uuid
from uuid import UUID

from asyncpg import Connection, Pool

from app.core.logging import get_logger
from app.domain.entities.account import Account
from app.domain.entities.idempotency_key import Transaction
from app.domain.entities.ledger_entry import LedgerEntry
from app.domain.exceptions import AccountNotFound, InsufficientFunds
from app.domain.repositories.account_repo import AccountRepository
from app.domain.repositories.ledger_repo import LedgerRepository
from app.domain.repositories.transfer_repo import TransactionRepository
from app.domain.value_objects.enums import AccountTypes, LedgerDirection
from app.infrastructure.db.transaction import transaction
from app.infrastructure.redis.cache import CacheService

logger = get_logger(__name__)


class SetBalanceUseCase:
    """Set account balance for a user."""

    def __init__(
        self,
        pool: Pool,
        account_repo: AccountRepository,
        transaction_repo: TransactionRepository,
        ledger_repo: LedgerRepository,
        cache: CacheService | None = None,
    ) -> None:
        self._pool = pool
        self._account_repo = account_repo
        self._transaction_repo = transaction_repo
        self._ledger_repo = ledger_repo
        self._cache = cache

    # ── Public entry point ───────────────────────────────

    async def execute(self, user_id: UUID, new_balance: int, currency: str) -> dict:
        currency = currency.upper()
        async with transaction(self._pool) as conn:
            account = await self._get_or_create_account(user_id, currency, conn)
            treasury = await self._get_treasury(conn, currency)

            delta = new_balance - account.balance
            if delta == 0:
                return self._build_response(user_id, account)

            if delta > 0 and treasury.balance < delta:
                raise InsufficientFunds("Treasury has insufficient balance")

            tx = await self._record_transaction(account, conn)
            await self._apply_balance_transfer(account, treasury, tx.id, delta, conn)
            await self._write_ledger_entries(account, treasury, tx.id, delta, conn)
            await self._transaction_repo.mark_completed(tx.idempotency_key, conn)

            account.balance = new_balance

        await self._update_caches(account, treasury)
        return self._build_response(user_id, account)

    # ── Account resolution ───────────────────────────────

    async def _get_or_create_account(
        self,
        user_id: UUID,
        currency: str,
        conn: Connection,
    ) -> Account:
        accounts = await self._account_repo.list_by_owner_id(user_id, conn)
        account = next(
            (
                a
                for a in accounts
                if a.currency.upper() == currency.upper() and a.is_active
            ),
            None,
        )
        if account is None:
            new_account = Account.create(user_id, currency=currency, owner_type="user")
            await self._account_repo.create(new_account, conn=conn)
            account = new_account
        return account

    async def _get_treasury(self, conn: Connection, currency: str) -> Account:
        treasury = await self._account_repo.get_by_account_type(
            AccountTypes.TREASURY,
            conn,
            currency,
        )
        if not treasury:
            raise AccountNotFound(
                f"Treasury account not found for currency '{currency}'"
            )
        return treasury

    # ── Transaction & ledger ─────────────────────────────

    async def _record_transaction(
        self, account: Account, conn: Connection
    ) -> Transaction:
        tx = Transaction.create(
            idempotency_key=f"set_balance:{account.id}:{uuid.uuid4()}",
            reference_type="REST_API",
            reference_id=str(account.id),
        )
        await self._transaction_repo.save(tx, conn)
        return tx

    async def _apply_balance_transfer(
        self,
        account: Account,
        treasury: Account,
        tx_id: UUID,
        delta: int,
        conn: Connection,
    ) -> None:
        amount = abs(delta)
        if delta > 0:
            await self._account_repo.debit(treasury.id, amount, conn)
            await self._account_repo.credit(account.id, amount, conn)
        else:
            await self._account_repo.credit(treasury.id, amount, conn)
            await self._account_repo.debit(account.id, amount, conn)

    async def _write_ledger_entries(
        self,
        account: Account,
        treasury: Account,
        tx_id: UUID,
        delta: int,
        conn: Connection,
    ) -> None:
        amount = abs(delta)
        user_dir = (
            LedgerDirection.DIRECTION_CREDIT
            if delta > 0
            else LedgerDirection.DIRECTION_DEBIT
        )
        treasury_dir = (
            LedgerDirection.DIRECTION_DEBIT
            if delta > 0
            else LedgerDirection.DIRECTION_CREDIT
        )
        await self._ledger_repo.insert_many(
            [
                LedgerEntry.create(
                    account_id=treasury.id,
                    transaction_id=tx_id,
                    amount=amount,
                    direction=treasury_dir,
                ),
                LedgerEntry.create(
                    account_id=account.id,
                    transaction_id=tx_id,
                    amount=amount,
                    direction=user_dir,
                ),
            ],
            conn,
        )

    # ── Cache ────────────────────────────────────────────

    async def _update_caches(self, account: Account, treasury: Account) -> None:
        if self._cache:
            await self._cache.invalidate_balance(account.id)
            await self._cache.invalidate_balance(treasury.id)

    # ── Response ─────────────────────────────────────────

    @staticmethod
    def _build_response(user_id: UUID, account: Account) -> dict:
        return {
            "user_id": str(user_id),
            "found": True,
            "cached": False,
            "balances": [
                {
                    "account_id": str(account.id),
                    "currency": account.currency,
                    "balance": account.balance,
                    "cached": False,
                }
            ],
        }
