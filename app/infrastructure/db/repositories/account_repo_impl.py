"""Concrete account repository — raw asyncpg SQL."""

from __future__ import annotations

import uuid
from app.core.logging import get_logger
from asyncpg import Connection

from app.domain.entities.account import Account
from app.domain.repositories.account_repo import AccountRepository
from app.domain.value_objects.enums import AccountTypes

logger = get_logger(__name__)

_SELECT_COLS = (
    "id, user_id, owner_type, balance, currency, is_active, created_at, updated_at"
)


class PgAccountRepository(AccountRepository):

    async def get_by_id(
        self, account_id: uuid.UUID, conn: Connection
    ) -> Account | None:
        row = await conn.fetchrow(
            f"SELECT {_SELECT_COLS} FROM accounts WHERE id = $1",
            account_id,
        )
        return self._to_entity(row) if row else None

    async def get_by_owner_id_for_update(
        self, user_id: uuid.UUID, conn: Connection
    ) -> Account | None:
        row = await conn.fetchrow(
            f"SELECT {_SELECT_COLS} FROM accounts WHERE user_id = $1 FOR UPDATE",
            user_id,
        )
        return self._to_entity(row) if row else None

    async def get_by_owner_id(
        self, user_id: uuid.UUID, conn: Connection
    ) -> Account | None:
        row = await conn.fetchrow(
            f"SELECT {_SELECT_COLS} FROM accounts WHERE user_id = $1 ORDER BY currency",
            user_id,
        )
        return self._to_entity(row) if row else None

    async def list_by_owner_id(
        self, user_id: uuid.UUID, conn: Connection
    ) -> list[Account]:
        rows = await conn.fetch(
            f"SELECT {_SELECT_COLS} FROM accounts WHERE user_id = $1 ORDER BY currency",
            user_id,
        )
        return [self._to_entity(row) for row in rows]

    async def get_for_update(
        self, account_id: uuid.UUID, conn: Connection
    ) -> Account | None:
        row = await conn.fetchrow(
            f"SELECT {_SELECT_COLS} FROM accounts WHERE id = $1 FOR UPDATE",
            account_id,
        )
        return self._to_entity(row) if row else None

    async def get_or_create_by_owner_id(
        self, user_id: uuid.UUID, conn: Connection, currency: str = "TOKEN"
    ) -> Account:
        account = await self.get_by_owner_id(user_id, conn)
        if account is not None:
            return account
        new_account = Account.create(user_id=user_id, currency=currency)
        await self.create(new_account, conn)
        return new_account

    async def get_by_account_type(
        self,
        type: AccountTypes,
        conn: Connection,
        currency: str = "TOKEN",
    ) -> Account | None:
        row = await conn.fetchrow(
            f"SELECT {_SELECT_COLS} FROM accounts WHERE owner_type = $1 AND currency = $2 LIMIT 1",
            type,
            currency,
        )
        return self._to_entity(row) if row else None

    async def update_balance(
        self, account_id: uuid.UUID, new_balance: int, conn: Connection
    ) -> None:
        await conn.execute(
            "UPDATE accounts SET balance = $1, updated_at = NOW() WHERE id = $2",
            new_balance,
            account_id,
        )

    async def debit(self, account_id: uuid.UUID, amount: int, conn: Connection) -> None:
        result = await conn.execute(
            "UPDATE accounts SET balance = balance - $1, updated_at = NOW() "
            "WHERE id = $2 AND balance >= $1",
            amount,
            account_id,
        )
        rows_affected = int(result.split()[-1])
        if rows_affected == 0:
            from app.domain.exceptions import InsufficientFunds

            raise InsufficientFunds(account_id, amount)

    async def credit(
        self, account_id: uuid.UUID, amount: int, conn: Connection
    ) -> None:
        await conn.execute(
            "UPDATE accounts SET balance = balance + $1, updated_at = NOW() WHERE id = $2",
            amount,
            account_id,
        )

    async def create(self, account: Account, conn: Connection) -> None:
        try:
            await conn.execute(
                "INSERT INTO accounts "
                "(id, user_id, owner_type, balance, currency, is_active, created_at, updated_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                account.id,
                account.user_id,
                account.owner_type,
                account.balance,
                account.currency,
                account.is_active,
                account.created_at,
                account.updated_at,
            )
        except Exception:
            logger.error(
                "account_create_failed",
                user_id=str(account.user_id),
                account_id=str(account.id),
            )
            raise

    @staticmethod
    def _to_entity(row) -> Account:
        return Account(
            id=row["id"],
            user_id=row["user_id"],
            owner_type=row["owner_type"],
            balance=row["balance"],
            currency=row["currency"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
