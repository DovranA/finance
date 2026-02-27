"""Concrete account repository — raw asyncpg SQL."""

from __future__ import annotations

import uuid
from app.core.logging import get_logger
from asyncpg import Connection

from app.domain.entities.account import Account
from app.domain.repositories.account_repo import AccountRepository

logger = get_logger(__name__)


class PgAccountRepository(AccountRepository):

    async def get_by_id(
        self, account_id: uuid.UUID, conn: Connection
    ) -> Account | None:
        row = await conn.fetchrow(
            "SELECT id, user_id, balance, currency, is_active, created_at, updated_at "
            "FROM accounts WHERE id = $1",
            account_id,
        )
        return self._to_entity(row) if row else None

    async def get_by_user_id(
        self, user_id: uuid.UUID, conn: Connection
    ) -> Account | None:
        row = await conn.fetchrow(
            "SELECT id, user_id, balance, currency, is_active, created_at, updated_at "
            "FROM accounts WHERE user_id = $1",
            user_id,
        )
        return self._to_entity(row) if row else None

    async def get_for_update(
        self, account_id: uuid.UUID, conn: Connection
    ) -> Account | None:
        row = await conn.fetchrow(
            "SELECT id, user_id, balance, currency, is_active, created_at, updated_at "
            "FROM accounts WHERE id = $1 FOR UPDATE",
            account_id,
        )
        return self._to_entity(row) if row else None

    async def get_or_create_by_user_id(
        self, user_id: uuid.UUID, conn: Connection, currency: str = "USD"
    ) -> Account:
        account = await self.get_by_user_id(user_id, conn)
        if account is not None:
            return account
        new_account = Account.create(user_id=user_id, currency=currency)
        await self.create(new_account, conn)
        return new_account

    async def update_balance(
        self, account_id: uuid.UUID, new_balance: int, conn: Connection
    ) -> None:
        await conn.execute(
            "UPDATE accounts SET balance = $1, updated_at = NOW() WHERE id = $2",
            new_balance,
            account_id,
        )

    async def debit(self, account_id: uuid.UUID, amount: int, conn: Connection) -> None:
        await conn.execute(
            "UPDATE accounts SET balance = balance - $1, updated_at = NOW() WHERE id = $2 AND balance >= $1",
            amount,
            account_id,
        )

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
                "INSERT INTO accounts (user_id, balance, currency, is_active, created_at, updated_at) "
                "VALUES ($1, $2, $3, $4, $5, $6)",
                account.user_id,
                account.balance,
                account.currency,
                account.is_active,
                account.created_at,
                account.updated_at,
            )
        except Exception as e:
            # Log the error with more context
            logger.error(f"Failed to create account for user_id={account.user_id}: {e}")
            raise

    @staticmethod
    def _to_entity(row) -> Account:
        return Account(
            id=row["id"],
            user_id=row["user_id"],
            balance=row["balance"],
            currency=row["currency"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
