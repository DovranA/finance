"""Redis async client setup."""

from __future__ import annotations

import redis.asyncio as redis
from redis.asyncio.cluster import ClusterNode, RedisCluster

from app.core.config import RedisSettings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_redis_pool(settings: RedisSettings) -> redis.Redis | RedisCluster:
    """Create a Redis client — a cluster client when REDIS_CLUSTER_ADDRS is
    set (Redis Cluster only supports db 0), otherwise a single-node pool."""
    if settings.cluster_addrs:
        client = RedisCluster(
            startup_nodes=[ClusterNode(h, p) for h, p in settings.nodes],
            password=settings.password or None,
            max_connections=settings.pool_size,
            decode_responses=True,
        )
        await client.initialize()
        logger.info("redis_cluster_connected", nodes=settings.nodes)
        return client

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


async def close_redis(client: redis.Redis | RedisCluster) -> None:
    """Gracefully close the Redis connection."""
    await client.aclose()
    logger.info("redis_closed")
