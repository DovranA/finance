"""Concrete ledger repository — raw asyncpg SQL, append-only."""

from __future__ import annotations

import uuid

import orjson
from asyncpg import Connection

from app.domain.entities.ledger_entry import LedgerEntry
from app.domain.repositories.ledger_repo import LedgerRepository


class PgLedgerRepository(LedgerRepository):

    async def insert(self, entry: LedgerEntry, conn: Connection) -> None:
        await conn.execute(
            "INSERT INTO ledger_entries "
            "(id, account_id, amount, currency, entry_type, reference_id, metadata, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            entry.id,
            entry.account_id,
            entry.amount,
            entry.currency,
            entry.entry_type,
            entry.reference_id,
            orjson.dumps(entry.metadata).decode(),
            entry.created_at,
        )

    async def get_by_account(
        self,
        account_id: uuid.UUID,
        conn: Connection,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LedgerEntry]:
        rows = await conn.fetch(
            "SELECT id, account_id, amount, currency, entry_type, reference_id, metadata, created_at "
            "FROM ledger_entries WHERE account_id = $1 "
            "ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            account_id,
            limit,
            offset,
        )
        return [self._to_entity(r) for r in rows]

    async def get_by_reference(
        self, reference_id: uuid.UUID, conn: Connection
    ) -> list[LedgerEntry]:
        rows = await conn.fetch(
            "SELECT id, account_id, amount, currency, entry_type, reference_id, metadata, created_at "
            "FROM ledger_entries WHERE reference_id = $1 "
            "ORDER BY created_at",
            reference_id,
        )
        return [self._to_entity(r) for r in rows]

    @staticmethod
    def _to_entity(row) -> LedgerEntry:
        meta = row["metadata"]
        if isinstance(meta, str):
            meta = orjson.loads(meta)
        return LedgerEntry(
            id=row["id"],
            account_id=row["account_id"],
            amount=row["amount"],
            currency=row["currency"],
            entry_type=row["entry_type"],
            reference_id=row["reference_id"],
            metadata=meta,
            created_at=row["created_at"],
        )
