from uuid import UUID
import uuid

from asyncpg import Pool

from app.core.logging import get_logger
from app.domain.entities.idempotency_key import Transaction
from app.domain.entities.ledger_entry import LedgerEntry
from app.domain.exceptions import AccountNotFound, CurrencyMismatch
from app.domain.repositories.account_repo import AccountRepository
from app.domain.repositories.transfer_repo import TransactionRepository
from app.domain.repositories.ledger_repo import LedgerRepository
from app.domain.value_objects.enums import AccountTypes, LedgerDirection
from app.infrastructure.db.transaction import transaction
from app.infrastructure.redis.cache import CacheService


logger = get_logger(__name__)


class SetBalanceUseCase:
    """Set account balance for a user. This is a write operation and should be used with caution."""

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

    async def execute(self, user_id: UUID, new_balance: int):

        async with transaction(self._pool) as conn:
            account = await self._account_repo.get_for_update(user_id, conn)
            pool = await self._account_repo.get_by_account_type(
                AccountTypes.TREASURY, conn
            )
            if not pool:
                raise AccountNotFound(f"{AccountTypes.TREASURY} not fount")
            if pool.balance <= new_balance:
                raise CurrencyMismatch("On Pool low balance")
            current_balance = account.balance
            delta = new_balance - current_balance

            if delta == 0:
                return

            tx = Transaction.create(
                idempotency_key=f"set_balance:{account.id}:{uuid.uuid4()}",
                reference_type="REST_API",
                reference_id=str(account.id),
            )

            await self._transaction_repo.save(tx, conn)

            await self._ledger_repo.insert_many(
                [
                    LedgerEntry.create(
                        account_id=pool.id,
                        transaction_id=tx.id,
                        amount=abs(delta),
                        direction=(
                            LedgerDirection.DIRECTION_DEBIT
                            if delta > 0
                            else LedgerDirection.DIRECTION_CREDIT
                        ),
                    ),
                    LedgerEntry.create(
                        account_id=account.id,
                        transaction_id=tx.id,
                        amount=abs(delta),
                        direction=(
                            LedgerDirection.DIRECTION_CREDIT
                            if delta > 0
                            else LedgerDirection.DIRECTION_DEBIT
                        ),
                    ),
                ],
                conn,
            )
            if delta > 0:
                await self._account_repo.debit(pool.id, abs(delta), conn)
                await self._account_repo.credit(account.id, abs(delta), conn)
            else:
                await self._account_repo.credit(pool.id, abs(delta), conn)
                await self._account_repo.debit(account.id, abs(delta), conn)
            account.balance = new_balance
            await self._transaction_repo.mark_completed(tx.idempotency_key, conn)
            if self._cache:
                await self._cache.set_cached_balance(account.id, account.balance)
                await self._cache.set_cached_balance(pool.id, account.balance)

        return {
            "user_id": str(user_id),
            "account_id": str(account.id),
            "balance": account.balance,
            "currency": account.currency,
            "found": True,
            "cached": False,
        }
