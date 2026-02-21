import pytest
from unittest.mock import AsyncMock, MagicMock
import uuid

@pytest.fixture
def mock_transaction(mocker):
    """Mock asyncpg Transaction."""
    tx = mocker.AsyncMock()
    return tx

@pytest.fixture
def mock_conn(mocker, mock_transaction):
    """Mock asyncpg Connection."""
    # We use a regular MagicMock for the connection setup so that 
    # sync methods like .transaction() return a value immediately
    # instead of returning a coroutine. 
    # But methods that are awaited in code should be AsyncMocks.
    conn = mocker.MagicMock()
    conn.transaction = mocker.Mock(return_value=mock_transaction)
    conn.execute = mocker.AsyncMock()
    conn.fetch = mocker.AsyncMock()
    conn.fetchrow = mocker.AsyncMock()
    conn.fetchval = mocker.AsyncMock()
    return conn

@pytest.fixture
def mock_pool(mocker, mock_conn):
    """Mock asyncpg Pool."""
    pool = mocker.AsyncMock()
    # pool.acquire is awaited: conn = await pool.acquire()
    pool.acquire.return_value = mock_conn
    # pool.release is awaited: await pool.release(conn)
    pool.release = mocker.AsyncMock()
    return pool

@pytest.fixture
def sample_user_id():
    return uuid.uuid4()

@pytest.fixture
def sample_account_id():
    return uuid.uuid4()
