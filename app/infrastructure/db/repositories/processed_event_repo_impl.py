"""Concrete processed event repository — idempotency via asyncpg."""

from __future__ import annotations

import uuid

from asyncpg import Connection

from app.domain.repositories.processed_event_repo import ProcessedEventRepository


class PgProcessedEventRepository(ProcessedEventRepository):

    async def exists(self, event_id: uuid.UUID, conn: Connection) -> bool:
        row = await conn.fetchrow(
            "SELECT 1 FROM processed_events WHERE event_id = $1",
            event_id,
        )
        return row is not None

    async def mark_processed(
        self, event_id: uuid.UUID, event_type: str, conn: Connection
    ) -> None:
        await conn.execute(
            "INSERT INTO processed_events (event_id, event_type, processed_at) "
            "VALUES ($1, $2, NOW()) ON CONFLICT (event_id) DO NOTHING",
            event_id,
            event_type,
        )
