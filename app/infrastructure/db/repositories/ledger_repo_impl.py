"""Concrete ledger repository — raw asyncpg SQL, append-only."""

from __future__ import annotations

import uuid

from asyncpg import Connection

from app.domain.entities.ledger_entry import LedgerEntry
from app.domain.repositories.ledger_repo import LedgerRepository


class PgLedgerRepository(LedgerRepository):

    async def insert(self, entry: LedgerEntry, conn: Connection) -> None:
        await conn.execute(
            "INSERT INTO ledger_entries "
            "(id, account_id, transaction_id, amount, direction, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6)",
            entry.id,
            entry.account_id,
            entry.transaction_id,
            entry.amount,
            entry.direction,
            entry.created_at,
        )

    async def insert_many(self, entries: list[LedgerEntry], conn: Connection) -> None:
        await conn.executemany(
            """
            INSERT INTO ledger_entries
            (id, account_id, transaction_id, amount, direction, created_at)
            VALUES ($1,$2,$3,$4,$5,$6)
            """,
            [
                (
                    e.id,
                    e.account_id,
                    e.transaction_id,
                    e.amount,
                    e.direction,
                    e.created_at,
                )
                for e in entries
            ],
        )

    async def get_by_account(
        self,
        account_id: uuid.UUID,
        conn: Connection,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LedgerEntry]:
        rows = await conn.fetch(
            "SELECT id, account_id, transaction_id, amount, direction, created_at "
            "FROM ledger_entries WHERE account_id = $1 "
            "ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            account_id,
            limit,
            offset,
        )
        return [self._to_entity(r) for r in rows]

    async def get_by_transaction(
        self, transaction_id: uuid.UUID, conn: Connection
    ) -> list[LedgerEntry]:
        rows = await conn.fetch(
            "SELECT id, account_id, transaction_id, amount, direction, created_at "
            "FROM ledger_entries WHERE transaction_id = $1 "
            "ORDER BY created_at",
            transaction_id,
        )
        return [self._to_entity(r) for r in rows]

    @staticmethod
    def _to_entity(row) -> LedgerEntry:
        return LedgerEntry(
            id=row["id"],
            account_id=row["account_id"],
            transaction_id=row["transaction_id"],
            amount=row["amount"],
            direction=row["direction"],
            created_at=row["created_at"],
        )
