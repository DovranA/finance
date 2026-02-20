"""Batch processor worker — periodic background process.

Runs in a loop, processing unprocessed reward batches using
SELECT ... FOR UPDATE SKIP LOCKED for horizontal scalability.
Multiple instances can run concurrently without conflict.
"""

from __future__ import annotations

import asyncio
import signal

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.infrastructure.db.connection import create_pool, close_pool
from app.infrastructure.db.repositories.account_repo_impl import PgAccountRepository
from app.infrastructure.db.repositories.ledger_repo_impl import PgLedgerRepository
from app.infrastructure.db.repositories.reward_batch_repo_impl import PgRewardBatchRepository
from app.infrastructure.db.repositories.treasury_repo_impl import PgTreasuryRepository
from app.infrastructure.redis.cache import CacheService
from app.infrastructure.redis.client import create_redis_pool, close_redis
from app.usecases.process_reward_batch import ProcessRewardBatchUseCase

logger = get_logger(__name__)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.app.log_level)

    logger.info("batch_processor_starting")

    # ── Initialize infrastructure ────────────────────────
    pool = await create_pool(settings.postgres)

    redis_client = None
    cache: CacheService | None = None
    try:
        redis_client = await create_redis_pool(settings.redis)
        cache = CacheService(redis_client)
    except Exception:
        logger.warning("redis_unavailable_continuing_without_cache")

    # ── Wire use case ────────────────────────────────────
    use_case = ProcessRewardBatchUseCase(
        pool=pool,
        account_repo=PgAccountRepository(),
        ledger_repo=PgLedgerRepository(),
        reward_batch_repo=PgRewardBatchRepository(),
        treasury_repo=PgTreasuryRepository(),
        cache=cache,
    )

    # ── Processing loop ──────────────────────────────────
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
        "batch_processor_started",
        batch_size=settings.batch.size,
        interval=settings.batch.interval_seconds,
    )

    while not stop_event.is_set():
        try:
            processed = await use_case.execute(batch_size=settings.batch.size)
            if processed > 0:
                logger.info("batch_cycle_completed", processed=processed)
        except Exception:
            logger.exception("batch_processing_error")

        # Wait for interval or until stop signal
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=settings.batch.interval_seconds,
            )
        except asyncio.TimeoutError:
            pass  # Normal — timeout means continue loop

    # ── Cleanup ──────────────────────────────────────────
    if redis_client:
        await close_redis(redis_client)
    await close_pool(pool)
    logger.info("batch_processor_stopped")


if __name__ == "__main__":
    asyncio.run(main())
