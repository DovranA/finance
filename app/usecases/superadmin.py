import uuid

from asyncpg import Pool

from app.domain.entities.account import Account
from app.domain.exceptions import AccountNotFound
from app.domain.repositories.account_repo import AccountRepository
from app.domain.value_objects.enums import AccountTypes
from app.infrastructure.db.transaction import transaction


class SuperAdminUseCase:
    def __init__(
        self,
        pool: Pool,
        account_repo: AccountRepository,
    ) -> None:
        self._pool = pool
        self._account_repo = account_repo

    async def set_treasury(self, new_balance: int, currency: str) -> Account:
        async with transaction(self._pool) as conn:
            account = await self._account_repo.get_by_account_type(
                AccountTypes.TREASURY, conn, currency
            )
            if not account:
                account = Account.create(
                    None, currency, AccountTypes.TREASURY, balance=new_balance
                )
                await self._account_repo.create(account, conn)

            await self._account_repo.update_balance(account.id, new_balance, conn)
            account.balance = new_balance
            return account

    async def get_treasury(self, currency: str = "TOKEN"):
        async with self._pool.acquire() as conn:
            account = await self._account_repo.get_by_account_type(
                AccountTypes.TREASURY, conn, currency
            )
            if not account:
                raise AccountNotFound("Treasury account not found")
            return account
