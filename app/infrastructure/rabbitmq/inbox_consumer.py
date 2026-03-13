"""RabbitMQ consumer that stores incoming actions into DB inbox table."""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.db.connection import close_pool, create_pool
from app.infrastructure.rabbitmq.connection import (
    create_channel,
    create_connection,
    declare_exchange,
    declare_queue,
)
from app.infrastructure.rabbitmq.consumer import RewardEvent, consume_messages

logger = get_logger(__name__)


async def _store_event(pool, event: RewardEvent) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO rule_action_inbox "
            "(event_id, event_code, user_id, role, metadata, status) "
            "VALUES ($1, $2, $3, $4, $5::jsonb, 'pending') "
            "ON CONFLICT (event_id) DO NOTHING",
            event.event_id,
            event.action_code,
            event.publisher_id,
            None,
            {
                "actor_id": str(event.actor_id),
                "publisher_id": str(event.publisher_id),
                "content_id": str(event.content_id),
                "timestamp": event.timestamp.isoformat(),
            },
        )


async def run_consumer() -> None:
    settings = get_settings()
    rabbit = settings.rabbitmq

    pool = await create_pool(settings.postgres)
    conn = await create_connection(rabbit)
    channel = await create_channel(conn, prefetch_count=rabbit.prefetch_count)
    exchange = await declare_exchange(channel, rabbit.exchange)
    queue = await declare_queue(
        channel, rabbit.queue_rewards, exchange, routing_key="#"
    )

    async def _handler(event: RewardEvent) -> None:
        await _store_event(pool, event)

    await queue.consume(lambda msg: consume_messages(msg, _handler))
    logger.info("rule_inbox_consumer_started", queue=rabbit.queue_rewards)

    try:
        await asyncio.Future()
    finally:
        await channel.close()
        await conn.close()
        await close_pool(pool)


if __name__ == "__main__":
    asyncio.run(run_consumer())
