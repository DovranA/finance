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

        deletion_events = [
            event for event in events if event.event_code == "user_deleted"
        ]
        staged_events = [
            event for event in events if event.event_code != "user_deleted"
        ]

        if deletion_events:
            try:
                await self._delete_user_accounts(deletion_events)
            except Exception:
                for event in deletion_events:
                    metrics.inc_inbox_events("delete_failed", event.event_code)
                raise

            for event in deletion_events:
                metrics.inc_inbox_events("delete_applied", event.event_code)

        if not staged_events:
            return

        records = [
            (
                event.event_id,
                event.event_code,
                event.user_id,
                event.role,
                json.dumps(event.metadata),
            )
            for event in staged_events
        ]

        for event in staged_events:
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
                for event in staged_events:
                    metrics.inc_inbox_events("insert_failed", event.event_code)
                raise

        for event in staged_events:
            metrics.inc_inbox_events("inserted", event.event_code)

    async def _delete_user_accounts(self, events: list[InboxEvent]) -> None:
        user_ids = list({event.user_id for event in events})
        if not user_ids:
            return

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE accounts "
                    "SET is_active = FALSE, updated_at = NOW() "
                    "WHERE user_id = ANY($1::uuid[]) AND is_active = TRUE",
                    user_ids,
                )
