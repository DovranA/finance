"""Use case service for persisting parsed inbox events."""

from __future__ import annotations

from asyncpg import Pool

from app.infrastructure.rabbitmq.event_types import InboxEvent


class InboxService:
    """Stores parsed RabbitMQ events into rule action inbox table."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def handle(self, events: list[InboxEvent]) -> None:
        if not events:
            return

        records = [
            (
                event.event_id,
                event.event_code,
                event.user_id,
                event.role,
                event.metadata,
            )
            for event in events
        ]

        async with self._pool.acquire() as conn:
            await conn.executemany(
                "INSERT INTO rule_action_inbox "
                "(event_id, event_code, user_id, role, metadata, status) "
                "VALUES ($1, $2, $3, $4, $5::jsonb, 'pending') "
                "ON CONFLICT (event_id) DO NOTHING",
                records,
            )
