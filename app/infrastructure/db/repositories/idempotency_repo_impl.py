"""Concrete transaction repository — raw asyncpg SQL."""

from __future__ import annotations

import uuid

import orjson
from asyncpg import Connection

from app.domain.entities.idempotency_key import Transaction
from app.domain.repositories.transfer_repo import TransactionRepository


class PgTransactionRepository(TransactionRepository):

    # ── queries ────────────────────────────────────────────────

    async def exists(self, idempotency_key: str, conn: Connection) -> bool:
        return await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM transactions WHERE idempotency_key = $1)",
            idempotency_key,
        )

    async def get_by_key(
        self, idempotency_key: str, conn: Connection
    ) -> Transaction | None:
        row = await conn.fetchrow(
            "SELECT id, idempotency_key, status, reference_type, reference_id, "
            "metadata, created_at, expires_at "
            "FROM transactions WHERE idempotency_key = $1",
            idempotency_key,
        )
        return self._to_entity(row) if row else None

    async def get_by_id(self, tx_id: uuid.UUID, conn: Connection) -> Transaction | None:
        row = await conn.fetchrow(
            "SELECT id, idempotency_key, status, reference_type, reference_id, "
            "metadata, created_at, expires_at "
            "FROM transactions WHERE id = $1",
            tx_id,
        )
        return self._to_entity(row) if row else None

    # ── commands ───────────────────────────────────────────────

    async def save(self, entry: Transaction, conn: Connection) -> None:
        await conn.execute(
            "INSERT INTO transactions "
            "(id, idempotency_key, status, reference_type, reference_id, "
            "metadata, created_at, expires_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            entry.id,
            entry.idempotency_key,
            entry.status,
            entry.reference_type,
            entry.reference_id,
            orjson.dumps(entry.metadata).decode(),
            entry.created_at,
            entry.expires_at,
        )

    async def mark_completed(self, idempotency_key: str, conn: Connection) -> None:
        await conn.execute(
            "UPDATE transactions SET status = 'completed' "
            "WHERE idempotency_key = $1",
            idempotency_key,
        )

    async def mark_failed(self, idempotency_key: str, conn: Connection) -> None:
        await conn.execute(
            "UPDATE transactions SET status = 'failed' WHERE idempotency_key = $1",
            idempotency_key,
        )

    async def delete_expired(self, conn: Connection) -> int:
        result: str = await conn.execute(
            "DELETE FROM transactions "
            "WHERE expires_at IS NOT NULL AND expires_at < NOW()",
        )
        return int(result.split()[-1])

    # ── mapping ────────────────────────────────────────────────

    @staticmethod
    def _to_entity(row) -> Transaction:
        meta = row["metadata"]
        if isinstance(meta, str):
            meta = orjson.loads(meta)
        return Transaction(
            id=row["id"],
            idempotency_key=row["idempotency_key"],
            status=row["status"],
            reference_type=row["reference_type"],
            reference_id=row["reference_id"],
            metadata=meta,
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )
