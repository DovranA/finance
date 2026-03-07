from uuid import UUID
import uuid

from asyncpg import Pool

from app.core.logging import get_logger
from app.domain.entities.idempotency_key import Transaction
from app.domain.entities.ledger_entry import LedgerEntry, DIRECTION_DEBIT
from app.domain.repositories.account_repo import AccountRepository
from app.domain.repositories.idempotency_repo import TransactionRepository
from app.domain.repositories.ledger_repo import LedgerRepository
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

    async def execute(self, user_id: UUID, amount: int) -> dict:
        """Set the balance for a user's account. This will overwrite the existing balance."""
        async with transaction(self._pool) as conn:
            account = await self._account_repo.get_by_owner_id(user_id, conn)
            if not account:
                raise ValueError("Account not found")

            # Create transaction record
            tx = Transaction.create(
                idempotency_key=f"set_balance:{account.id}:{uuid.uuid4()}",
                reference_type="REST_API",
                reference_id=str(account.id),
            )
            await self._transaction_repo.save(tx, conn)

            # Update balance
            await self._account_repo.update_balance(account.id, amount, conn)

            # Record in ledger
            await self._ledger_repo.insert(
                LedgerEntry.create(
                    account_id=account.id,
                    transaction_id=tx.id,
                    amount=amount,
                    direction=DIRECTION_DEBIT,
                ),
                conn,
            )

            # Mark transaction completed
            await self._transaction_repo.mark_completed(tx.idempotency_key, conn)

            # Invalidate cache
            if self._cache:
                await self._cache.set_cached_balance(
                    account_id=account.id, balance=amount
                )

        return {"user_id": str(user_id), "new_balance": amount}
