"""RabbitMQ event consumer worker — standalone async process."""

from __future__ import annotations

import asyncio
import signal
from functools import partial

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.infrastructure.db.connection import create_pool, close_pool
from app.infrastructure.db.repositories.account_repo_impl import PgAccountRepository
from app.infrastructure.db.repositories.actor_action_repo_impl import PgActorActionRepository
from app.infrastructure.db.repositories.economic_action_repo_impl import PgEconomicActionRepository
from app.infrastructure.db.repositories.ledger_repo_impl import PgLedgerRepository
from app.infrastructure.db.repositories.processed_event_repo_impl import PgProcessedEventRepository
from app.infrastructure.db.repositories.reward_batch_repo_impl import PgRewardBatchRepository
from app.infrastructure.rabbitmq.connection import (
    create_connection,
    create_channel,
    declare_exchange,
    declare_queue,
)
from app.infrastructure.rabbitmq.consumer import RewardEvent, consume_messages
from app.infrastructure.redis.cache import CacheService
from app.infrastructure.redis.client import create_redis_pool, close_redis
from app.usecases.process_reward_event import ProcessRewardEventUseCase

logger = get_logger(__name__)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.app.log_level)

    logger.info("event_consumer_starting")

    # ── Initialize infrastructure ────────────────────────
    pool = await create_pool(settings.postgres)

    redis_client = None
    cache: CacheService | None = None
    try:
        redis_client = await create_redis_pool(settings.redis)
        cache = CacheService(redis_client)
    except Exception:
        logger.warning("redis_unavailable_continuing_without_cache")

    rmq_connection = await create_connection(settings.rabbitmq)
    channel = await create_channel(rmq_connection, settings.rabbitmq.prefetch_count)
    exchange = await declare_exchange(channel, settings.rabbitmq.exchange)
    queue = await declare_queue(
        channel, settings.rabbitmq.queue_rewards, exchange, routing_key="reward.#"
    )

    # ── Wire use case ────────────────────────────────────
    use_case = ProcessRewardEventUseCase(
        pool=pool,
        account_repo=PgAccountRepository(),
        ledger_repo=PgLedgerRepository(),
        actor_action_repo=PgActorActionRepository(),
        economic_action_repo=PgEconomicActionRepository(),
        reward_batch_repo=PgRewardBatchRepository(),
        processed_event_repo=PgProcessedEventRepository(),
        cache=cache,
    )

    async def handle_event(event: RewardEvent) -> None:
        await use_case.execute(event)

    # ── Start consuming ──────────────────────────────────
    await queue.consume(partial(consume_messages, handler=handle_event))
    logger.info("event_consumer_started", queue=settings.rabbitmq.queue_rewards)

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
            # Windows doesn't support add_signal_handler
            pass

    await stop_event.wait()

    # ── Cleanup ──────────────────────────────────────────
    await rmq_connection.close()
    if redis_client:
        await close_redis(redis_client)
    await close_pool(pool)
    logger.info("event_consumer_stopped")


if __name__ == "__main__":
    asyncio.run(main())
