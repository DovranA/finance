import pytest
import asyncio
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_debug_async_mock():
    mock = AsyncMock()
    # If we call an AsyncMock, it returns a coroutine
    coro = mock()
    # If we don't await coro, we get the warning
    await coro # This should prevent the warning
    assert mock.called
