import uuid

from asyncpg import Pool

from app.core.logging import get_logger
from app.domain.entities.idempotency_key import Transaction
from app.domain.entities.ledger_entry import (
    LedgerEntry,
    DIRECTION_CREDIT,
    DIRECTION_DEBIT,
)
from app.domain.exceptions import (
    AccountNotFound,
    DuplicateOperation,
    InsufficientFunds,
)
from app.domain.repositories.account_repo import AccountRepository
from app.domain.repositories.idempotency_repo import TransactionRepository
from app.domain.repositories.ledger_repo import LedgerRepository
from app.infrastructure.db.transaction import transaction
from app.infrastructure.redis.cache import CacheService

logger = get_logger(__name__)


class TransferUseCase:
    def __init__(
        self,
        pool: Pool,
        account_repo: AccountRepository,
        transaction_repo: TransactionRepository,
        ledger_repo: LedgerRepository,
        cache: CacheService | None = None,
    ):
        self._pool = pool
        self._account_repo = account_repo
        self._transaction_repo = transaction_repo
        self._ledger_repo = ledger_repo
        self._cache = cache

    async def execute(
        self,
        *,
        from_account_id: uuid.UUID,
        to_account_id: uuid.UUID,
        amount: int,
        idempotency_key: str,
        reference_type: str = "transfer",
        metadata: dict | None = None,
    ) -> dict:
        async with transaction(self._pool) as conn:
            # Idempotency check
            existing = await self._transaction_repo.get_by_key(idempotency_key, conn)
            if existing and existing.status == "completed":
                raise DuplicateOperation()

            # Lock accounts in deterministic order to prevent deadlocks
            ids = sorted([from_account_id, to_account_id])
            acct_a = await self._account_repo.get_for_update(ids[0], conn)
            acct_b = await self._account_repo.get_for_update(ids[1], conn)

            from_acct = acct_a if acct_a and acct_a.id == from_account_id else acct_b
            to_acct = acct_b if acct_b and acct_b.id == to_account_id else acct_a

            if from_acct is None:
                raise AccountNotFound(f"Source account {from_account_id} not found")
            if to_acct is None:
                raise AccountNotFound(f"Destination account {to_account_id} not found")

            from_acct.ensure_active()
            to_acct.ensure_active()

            if from_acct.balance < amount:
                raise InsufficientFunds()

            # Create transaction record
            tx = Transaction.create(
                idempotency_key=idempotency_key,
                reference_type=reference_type,
                reference_id=str(from_account_id),
                metadata=metadata or {},
            )
            await self._transaction_repo.save(tx, conn)

            # Debit source
            await self._account_repo.debit(from_account_id, amount, conn)
            await self._ledger_repo.insert(
                LedgerEntry.create(
                    account_id=from_account_id,
                    transaction_id=tx.id,
                    amount=amount,
                    direction=DIRECTION_DEBIT,
                ),
                conn,
            )

            # Credit destination
            await self._account_repo.credit(to_account_id, amount, conn)
            await self._ledger_repo.insert(
                LedgerEntry.create(
                    account_id=to_account_id,
                    transaction_id=tx.id,
                    amount=amount,
                    direction=DIRECTION_CREDIT,
                ),
                conn,
            )

            # Mark completed
            await self._transaction_repo.mark_completed(idempotency_key, conn)

            # Invalidate caches
            if self._cache:
                await self._cache.invalidate_balance(from_account_id)
                await self._cache.invalidate_balance(to_account_id)

        return {
            "transaction_id": str(tx.id),
            "from_account_id": str(from_account_id),
            "to_account_id": str(to_account_id),
            "amount": amount,
            "status": "completed",
        }
