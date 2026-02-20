"""Redis async client setup."""

from __future__ import annotations

import redis.asyncio as redis

from app.core.config import RedisSettings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_redis_pool(settings: RedisSettings) -> redis.Redis:
    """Create a Redis connection pool."""
    pool = redis.ConnectionPool.from_url(
        settings.url,
        max_connections=settings.pool_size,
        decode_responses=True,
    )
    client = redis.Redis(connection_pool=pool)
    # Verify connectivity
    await client.ping()
    logger.info(
        "redis_connected",
        host=settings.host,
        port=settings.port,
        db=settings.db,
    )
    return client


async def close_redis(client: redis.Redis) -> None:
    """Gracefully close the Redis connection."""
    await client.aclose()
    logger.info("redis_closed")
