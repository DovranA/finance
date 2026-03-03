"""Shared test fixtures."""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_transaction(mocker):
    """Mock asyncpg Transaction."""
    tx = mocker.AsyncMock()
    return tx


@pytest.fixture
def mock_conn(mocker, mock_transaction):
    """Mock asyncpg Connection.

    Sync methods like .transaction() return a value immediately;
    awaited methods (execute, fetch, etc.) are AsyncMocks.
    """
    conn = mocker.MagicMock()
    conn.transaction = mocker.Mock(return_value=mock_transaction)
    conn.execute = mocker.AsyncMock()
    conn.fetch = mocker.AsyncMock()
    conn.fetchrow = mocker.AsyncMock()
    conn.fetchval = mocker.AsyncMock()
    return conn


@pytest.fixture
def mock_pool(mocker, mock_conn):
    """Mock asyncpg Pool.

    Supports both:
      - ``async with pool.acquire() as conn``  (context manager)
      - ``conn = await pool.acquire()``         (direct await)
      - ``transaction(pool)``                    (via patched context manager)
    """
    pool = mocker.MagicMock()

    # Make pool.acquire() return an async context manager yielding mock_conn
    acm = mocker.MagicMock()
    acm.__aenter__ = mocker.AsyncMock(return_value=mock_conn)
    acm.__aexit__ = mocker.AsyncMock(return_value=False)
    pool.acquire.return_value = acm

    pool.release = mocker.AsyncMock()

    # Patch the transaction context manager used by use cases
    @asynccontextmanager
    async def _fake_transaction(p):
        yield mock_conn

    mocker.patch(
        "app.infrastructure.db.transaction.transaction",
        side_effect=_fake_transaction,
    )

    return pool


@pytest.fixture
def sample_user_id():
    return uuid.uuid4()


@pytest.fixture
def sample_account_id():
    return uuid.uuid4()
