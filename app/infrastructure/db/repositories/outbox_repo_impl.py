"""Concrete outbox repository — raw asyncpg SQL."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import orjson
from asyncpg import Connection

from app.domain.entities.outbox_message import OutboxMessage
from app.domain.repositories.outbox_repo import OutboxRepository


class PgOutboxRepository(OutboxRepository):

    async def insert(self, message: OutboxMessage, conn: Connection) -> None:
        await conn.execute(
            """
            INSERT INTO outbox_messages
                (id, aggregate_type, aggregate_id, event_type,
                 payload, status, retry_count, max_retries, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            message.id,
            message.aggregate_type,
            message.aggregate_id,
            message.event_type,
            orjson.dumps(message.payload).decode(),
            message.status,
            message.retry_count,
            message.max_retries,
            message.created_at,
        )

    async def fetch_pending(
        self, limit: int, conn: Connection
    ) -> list[OutboxMessage]:
        rows = await conn.fetch(
            """
            SELECT id, aggregate_type, aggregate_id, event_type,
                   payload, status, retry_count, max_retries,
                   created_at, sent_at
            FROM outbox_messages
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT $1
            FOR UPDATE SKIP LOCKED
            """,
            limit,
        )
        return [self._to_entity(r) for r in rows]

    async def mark_sent(
        self, message_id: uuid.UUID, conn: Connection
    ) -> None:
        await conn.execute(
            "UPDATE outbox_messages SET status = 'sent', sent_at = $1 WHERE id = $2",
            datetime.now(timezone.utc),
            message_id,
        )

    async def mark_failed(
        self, message_id: uuid.UUID, retry_count: int, conn: Connection
    ) -> None:
        status = "failed" if retry_count >= 5 else "pending"
        await conn.execute(
            "UPDATE outbox_messages SET status = $1, retry_count = $2 WHERE id = $3",
            status,
            retry_count,
            message_id,
        )

    async def delete_sent_older_than(
        self, days: int, conn: Connection
    ) -> int:
        result = await conn.execute(
            "DELETE FROM outbox_messages WHERE status = 'sent' AND sent_at < NOW() - ($1 || ' days')::INTERVAL",
            str(days),
        )
        # asyncpg returns "DELETE N"
        return int(result.split()[-1])

    @staticmethod
    def _to_entity(row) -> OutboxMessage:
        payload = row["payload"]
        if isinstance(payload, str):
            payload = orjson.loads(payload)
        return OutboxMessage(
            id=row["id"],
            aggregate_type=row["aggregate_type"],
            aggregate_id=row["aggregate_id"],
            event_type=row["event_type"],
            payload=payload,
            status=row["status"],
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
            created_at=row["created_at"],
            sent_at=row["sent_at"],
        )
