"""asyncpg connection pool management."""

from __future__ import annotations

import asyncpg
from asyncpg import Pool

from app.core.config import PostgresSettings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_pool(settings: PostgresSettings) -> Pool:
    """Create and return an asyncpg connection pool."""
    pool = await asyncpg.create_pool(
        dsn=settings.dsn,
        min_size=settings.pool_min,
        max_size=settings.pool_max,
        command_timeout=30,
        server_settings={
            "application_name": "finance-service",
        },
    )
    logger.info(
        "database_pool_created",
        host=settings.host,
        port=settings.port,
        db=settings.db,
        min_size=settings.pool_min,
        max_size=settings.pool_max,
    )
    return pool


async def close_pool(pool: Pool) -> None:
    """Gracefully close the connection pool."""
    await pool.close()
    logger.info("database_pool_closed")
