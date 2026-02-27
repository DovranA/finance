from app.domain.repositories.account_repo import AccountRepository
from app.domain.repositories.idempotency_repo import IdempotencyRepository
from app.domain.repositories.ledger_repo import LedgerRepository


class CreateLedgerEntryUseCase:

    def __init__(
        self,
        account_repo: AccountRepository,
        ledger_repo: LedgerRepository,
        idempotency_repo: IdempotencyRepository,
        transaction_manager,
    ):
        self.account_repo = account_repo
        self.ledger_repo = ledger_repo
        self.idempotency_repo = idempotency_repo
        self.tx = transaction_manager

    async def execute(self, cmd: CreateLedgerEntryCommand) -> None:
        # 1. Idempotency fast check
        if await self.idempotency_repo.exists(cmd.idempotency_key):
            raise DuplicateOperation(cmd.idempotency_key)

        async with self.tx():  # DB transaction
            # 2. Load account
            account = await self.account_repo.get_by_id(cmd.account_id)
            account.ensure_active()

            # 3. Business validation
            if cmd.entry_type == LedgerEntryType.DEBIT:
                if not account.can_debit(cmd.amount):
                    raise InsufficientFunds(account.id, cmd.amount)

            # 4. Create ledger entry
            entry = LedgerEntry.create(
                account_id=cmd.account_id,
                amount=cmd.amount,
                entry_type=cmd.entry_type,
                reference_id=cmd.reference_id,
                reference_type=cmd.reference_type,
                idempotency_key=cmd.idempotency_key,
                currency=cmd.currency,
                metadata=cmd.metadata,
            )

            # 5. Persist ledger
            await self.ledger_repo.insert(entry)

            # 6. Update balance
            if cmd.entry_type == LedgerEntryType.CREDIT:
                await self.account_repo.credit(cmd.account_id, cmd.amount)
            else:
                await self.account_repo.debit(cmd.account_id, cmd.amount)

            # 7. Save idempotency key
            await self.idempotency_repo.save(cmd.idempotency_key)
