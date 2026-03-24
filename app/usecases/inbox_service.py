"""Use case service for persisting parsed inbox events."""

from __future__ import annotations

import json

from asyncpg import Pool

from app.core.metrics import register_metrics
from app.infrastructure.rabbitmq.event_types import InboxEvent


class InboxService:
    """Stores parsed RabbitMQ events into rule action inbox table."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def handle(self, events: list[InboxEvent]) -> None:
        if not events:
            return

        metrics = await register_metrics()

        records = [
            (
                event.event_id,
                event.event_code,
                event.user_id,
                event.role,
                json.dumps(event.metadata),
            )
            for event in events
        ]

        for event in events:
            metrics.inc_inbox_events("queued_for_insert", event.event_code)

        async with self._pool.acquire() as conn:
            try:
                await conn.executemany(
                    "INSERT INTO rule_action_inbox "
                    "(event_id, event_code, user_id, role, metadata, status) "
                    "VALUES ($1, $2, $3, $4, $5::jsonb, 'pending') "
                    "ON CONFLICT (event_id) DO NOTHING",
                    records,
                )
            except Exception:
                for event in events:
                    metrics.inc_inbox_events("insert_failed", event.event_code)
                raise

        for event in events:
            metrics.inc_inbox_events("inserted", event.event_code)
