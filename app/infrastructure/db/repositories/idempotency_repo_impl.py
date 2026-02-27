"""Concrete idempotency-key repository — raw asyncpg SQL."""

from __future__ import annotations

from asyncpg import Connection

from app.domain.entities.idempotency_key import IdempotencyKey
from app.domain.repositories.idempotency_repo import IdempotencyRepository


class PgIdempotencyRepository(IdempotencyRepository):

    # ── queries ────────────────────────────────────────────────

    async def exists(self, key: str, conn: Connection) -> bool:
        return await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM idempotency_keys WHERE key = $1)",
            key,
        )

    async def get_by_key(self, key: str, conn: Connection) -> IdempotencyKey | None:
        row = await conn.fetchrow(
            "SELECT id, key, status, response_code, response_body, "
            "created_at, expires_at "
            "FROM idempotency_keys WHERE key = $1",
            key,
        )
        return self._to_entity(row) if row else None

    # ── commands ───────────────────────────────────────────────

    async def save(self, entry: IdempotencyKey, conn: Connection) -> None:
        await conn.execute(
            "INSERT INTO idempotency_keys "
            "(id, key, status, response_code, response_body, created_at, expires_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7)",
            entry.id,
            entry.key,
            entry.status,
            entry.response_code,
            entry.response_body,
            entry.created_at,
            entry.expires_at,
        )

    async def mark_completed(
        self,
        key: str,
        response_code: int,
        response_body: str,
        conn: Connection,
    ) -> None:
        await conn.execute(
            "UPDATE idempotency_keys "
            "SET status = 'completed', response_code = $1, response_body = $2 "
            "WHERE key = $3",
            response_code,
            response_body,
            key,
        )

    async def mark_failed(self, key: str, conn: Connection) -> None:
        await conn.execute(
            "UPDATE idempotency_keys SET status = 'failed' WHERE key = $1",
            key,
        )

    async def delete_expired(self, conn: Connection) -> int:
        result: str = await conn.execute(
            "DELETE FROM idempotency_keys WHERE expires_at IS NOT NULL AND expires_at < NOW()",
        )
        # asyncpg returns e.g. "DELETE 42"
        return int(result.split()[-1])

    # ── mapping ────────────────────────────────────────────────

    @staticmethod
    def _to_entity(row) -> IdempotencyKey:
        return IdempotencyKey(
            id=row["id"],
            key=row["key"],
            status=row["status"],
            response_code=row["response_code"],
            response_body=row["response_body"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )
