"""Concrete treasury repository — raw asyncpg SQL."""

from __future__ import annotations

from asyncpg import Connection


class PgTreasuryRepository:
    """Simple repository for treasury account balance updates."""

    async def credit(
        self, account_type: str, amount: int, conn: Connection
    ) -> None:
        await conn.execute(
            "UPDATE treasury_account "
            "SET balance = balance + $1, updated_at = NOW() "
            "WHERE account_type = $2",
            amount,
            account_type,
        )

    async def get_balance(
        self, account_type: str, conn: Connection
    ) -> int:
        row = await conn.fetchrow(
            "SELECT balance FROM treasury_account WHERE account_type = $1",
            account_type,
        )
        return row["balance"] if row else 0
