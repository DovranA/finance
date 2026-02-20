"""Outbox Relay Worker — polls outbox_messages and publishes to RabbitMQ.

This is the heart of the Transactional Outbox pattern. It guarantees
at-least-once delivery: events are committed to the outbox table inside
the business transaction, then this worker picks them up and publishes
to RabbitMQ. If publishing succeeds, the row is marked 'sent'.

Multiple instances are safe thanks to FOR UPDATE SKIP LOCKED.
"""

from __future__ import annotations

import asyncio
import signal

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.infrastructure.db.connection import create_pool, close_pool
from app.infrastructure.db.repositories.outbox_repo_impl import PgOutboxRepository
from app.infrastructure.db.transaction import transaction
from app.infrastructure.rabbitmq.connection import (
    create_connection,
    create_channel,
    declare_exchange,
)
from app.infrastructure.rabbitmq.publisher import EventPublisher

logger = get_logger(__name__)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.app.log_level)

    logger.info("outbox_relay_starting")

    # ── Infrastructure ───────────────────────────────────
    pool = await create_pool(settings.postgres)
    rmq_connection = await create_connection(settings.rabbitmq)
    channel = await create_channel(rmq_connection, prefetch_count=1)
    exchange = await declare_exchange(channel, settings.rabbitmq.exchange)

    publisher = EventPublisher(exchange)
    outbox_repo = PgOutboxRepository()

    # ── Relay configuration ──────────────────────────────
    poll_interval = float(getattr(settings.app, "outbox_poll_interval", 1.0))
    batch_size = int(getattr(settings.app, "outbox_batch_size", 200))
    cleanup_interval = 3600  # cleanup sent messages every hour
    cleanup_days = 7

    # ── Graceful shutdown ────────────────────────────────
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("shutdown_signal_received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    logger.info(
        "outbox_relay_started",
        poll_interval=poll_interval,
        batch_size=batch_size,
    )

    cycles_since_cleanup = 0

    while not stop_event.is_set():
        try:
            published = 0

            async with transaction(pool) as conn:
                messages = await outbox_repo.fetch_pending(batch_size, conn)

                for msg in messages:
                    try:
                        await publisher.publish(
                            routing_key=msg.event_type,
                            body=msg.payload,
                        )
                        await outbox_repo.mark_sent(msg.id, conn)
                        published += 1

                    except Exception:
                        logger.exception(
                            "outbox_publish_failed",
                            message_id=str(msg.id),
                            event_type=msg.event_type,
                            retry_count=msg.retry_count,
                        )
                        msg.mark_failed()
                        await outbox_repo.mark_failed(
                            msg.id, msg.retry_count, conn
                        )

            if published > 0:
                logger.info("outbox_relay_cycle", published=published)

            # ── Periodic cleanup of old sent messages ────
            cycles_since_cleanup += 1
            if cycles_since_cleanup * poll_interval >= cleanup_interval:
                cycles_since_cleanup = 0
                try:
                    async with transaction(pool) as conn:
                        deleted = await outbox_repo.delete_sent_older_than(
                            cleanup_days, conn
                        )
                    if deleted > 0:
                        logger.info("outbox_cleanup", deleted=deleted)
                except Exception:
                    logger.exception("outbox_cleanup_error")

        except Exception:
            logger.exception("outbox_relay_error")

        # Wait for interval or stop signal
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=poll_interval,
            )
        except asyncio.TimeoutError:
            pass

    # ── Cleanup ──────────────────────────────────────────
    await rmq_connection.close()
    await close_pool(pool)
    logger.info("outbox_relay_stopped")


if __name__ == "__main__":
    asyncio.run(main())
