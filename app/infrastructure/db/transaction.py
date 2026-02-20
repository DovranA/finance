"""Database transaction manager — async context manager."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from asyncpg import Connection, Pool

from app.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def transaction(pool: Pool) -> AsyncGenerator[Connection, None]:
    """Acquire a connection, begin transaction, commit or rollback.

    Usage::

        async with transaction(pool) as conn:
            await conn.execute("INSERT INTO ...")
            await conn.execute("UPDATE ...")
    """
    conn: Connection = await pool.acquire()
    tx = conn.transaction()
    try:
        await tx.start()
        yield conn
        await tx.commit()
    except Exception:
        await tx.rollback()
        logger.exception("transaction_rollback")
        raise
    finally:
        await pool.release(conn)
