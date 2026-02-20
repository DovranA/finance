"""Redis cache helpers — economic config caching and idempotency TTL."""

from __future__ import annotations

import uuid
from typing import Any

import orjson
import redis.asyncio as redis

from app.core.logging import get_logger

logger = get_logger(__name__)

# TTLs in seconds
ECONOMIC_CONFIG_TTL = 300       # 5 minutes
IDEMPOTENCY_TTL = 3600          # 1 hour
BALANCE_CACHE_TTL = 60          # 1 minute


class CacheService:
    """Redis-backed caching for hot paths.

    Redis is NOT the source of truth — always falls back to DB.
    """

    def __init__(self, client: redis.Redis) -> None:
        self._redis = client

    # ── Economic Config Cache ────────────────────────────

    async def get_economic_config(self, action_code: str) -> dict[str, Any] | None:
        key = f"econ:config:{action_code.upper()}"
        data = await self._redis.get(key)
        if data is None:
            return None
        return orjson.loads(data)

    async def set_economic_config(
        self, action_code: str, config: dict[str, Any]
    ) -> None:
        key = f"econ:config:{action_code.upper()}"
        await self._redis.set(key, orjson.dumps(config), ex=ECONOMIC_CONFIG_TTL)

    async def invalidate_economic_config(self, action_code: str) -> None:
        key = f"econ:config:{action_code.upper()}"
        await self._redis.delete(key)

    # ── Idempotency Short-TTL Cache ──────────────────────

    async def is_event_processed(self, event_id: uuid.UUID) -> bool:
        """Quick Redis check before hitting DB."""
        key = f"idem:{event_id}"
        return await self._redis.exists(key) == 1

    async def mark_event_processed(self, event_id: uuid.UUID) -> None:
        key = f"idem:{event_id}"
        await self._redis.set(key, "1", ex=IDEMPOTENCY_TTL)

    # ── Balance Cache ────────────────────────────────────

    async def get_cached_balance(self, account_id: uuid.UUID) -> int | None:
        key = f"bal:{account_id}"
        val = await self._redis.get(key)
        return int(val) if val is not None else None

    async def set_cached_balance(
        self, account_id: uuid.UUID, balance: int
    ) -> None:
        key = f"bal:{account_id}"
        await self._redis.set(key, str(balance), ex=BALANCE_CACHE_TTL)

    async def invalidate_balance(self, account_id: uuid.UUID) -> None:
        key = f"bal:{account_id}"
        await self._redis.delete(key)
