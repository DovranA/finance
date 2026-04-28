"""Redis cache helpers — economic config caching and idempotency TTL."""

from __future__ import annotations

import uuid
from typing import Any

import orjson
import redis.asyncio as redis

from app.core.logging import get_logger

logger = get_logger(__name__)

# TTLs in seconds
ECONOMIC_CONFIG_TTL = 300  # 5 minutes
IDEMPOTENCY_TTL = 3600  # 1 hour
BALANCE_CACHE_TTL = 60  # 1 minute
RULE_ACTION_STAGING_TTL = 7200  # 2 hours
TOP_BY_AMOUNT_CACHE_TTL = 300  # 5 minutes
TOP_BY_AMOUNT_PREV_CACHE_TTL = 60 * 60 * 24  # 1 day


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

    # ── Rule Cache ──────────────────────

    RULES_CACHE_TTL = 300  # 5 minutes

    async def get_cached_rules(self, event_code: str) -> list[dict[str, Any]] | None:
        key = f"rules:{event_code}"
        data = await self._redis.get(key)
        if data is None:
            return None
        return orjson.loads(data)

    async def set_cached_rules(
        self, event_code: str, rules: list[dict[str, Any]]
    ) -> None:
        key = f"rules:{event_code}"
        await self._redis.set(key, orjson.dumps(rules), ex=self.RULES_CACHE_TTL)

    async def invalidate_rules(self, event_code: str | None = None) -> None:
        if event_code:
            await self._redis.delete(f"rules:{event_code}")
        else:
            async for key in self._redis.scan_iter(match="rules:*"):
                await self._redis.delete(key)

    # ── Statistics Cache ────────────────────────────────

    async def get_cached_top_by_amount(
        self,
        limit: int,
    ) -> list[dict[str, Any]] | None:
        key = f"stats:top_by_amount:all_time:{limit}"
        data = await self._redis.get(key)
        if data is None:
            return None
        return orjson.loads(data)

    async def set_cached_top_by_amount(
        self,
        limit: int,
        rows: list[dict[str, Any]],
    ) -> None:
        key = f"stats:top_by_amount:all_time:{limit}"
        await self._redis.set(key, orjson.dumps(rows), ex=TOP_BY_AMOUNT_CACHE_TTL)

    async def get_cached_top_by_amount_page(
        self,
        page: int,
        limit: int,
        currency: str,
    ) -> dict[str, Any] | None:
        key = f"stats:top_by_amount:{currency.upper()}:{page}:{limit}"
        data = await self._redis.get(key)
        if data is None:
            return None
        return orjson.loads(data)

    async def set_cached_top_by_amount_page(
        self,
        page: int,
        limit: int,
        currency: str,
        payload: dict[str, Any],
    ) -> None:
        key = f"stats:top_by_amount:{currency.upper()}:{page}:{limit}"
        await self._redis.set(key, orjson.dumps(payload), ex=TOP_BY_AMOUNT_CACHE_TTL)

    async def get_cached_top_by_amount_previous_page(
        self,
        page: int,
        limit: int,
        currency: str,
    ) -> dict[str, Any] | None:
        key = f"stats:top_by_amount:prev:{currency.upper()}:{page}:{limit}"
        data = await self._redis.get(key)
        if data is None:
            return None
        return orjson.loads(data)

    async def set_cached_top_by_amount_previous_page(
        self,
        page: int,
        limit: int,
        currency: str,
        payload: dict[str, Any],
    ) -> None:
        key = f"stats:top_by_amount:prev:{currency.upper()}:{page}:{limit}"
        await self._redis.set(
            key,
            orjson.dumps(payload),
            ex=TOP_BY_AMOUNT_PREV_CACHE_TTL,
        )

    # ── One-Time-Per-Event Cache (1 day) ──────────────────

    ONE_TIME_TTL = 86400  # 1 day

    async def is_one_time_done(self, account_id: uuid.UUID, event_id: str) -> bool:
        key = f"ot:{account_id}:{event_id}"
        return await self._redis.exists(key) == 1

    async def mark_one_time_done(self, account_id: uuid.UUID, event_id: str) -> None:
        key = f"ot:{account_id}:{event_id}"
        await self._redis.set(key, "1", ex=self.ONE_TIME_TTL)

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

    async def set_cached_balance(self, account_id: uuid.UUID, balance: int) -> None:
        key = f"bal:{account_id}"
        await self._redis.set(key, str(balance), ex=BALANCE_CACHE_TTL)

    async def invalidate_balance(self, account_id: uuid.UUID) -> None:
        key = f"bal:{account_id}"
        await self._redis.delete(key)

    # ── Rule Action Staging (RabbitMQ -> batch worker) ──

    RULE_ACTION_EVENTS_KEY = "rule_actions:events"

    async def stage_rule_action(self, event_code: str, payload: dict[str, Any]) -> None:
        key = f"rule_actions:{event_code}"
        await self._redis.rpush(key, orjson.dumps(payload))
        await self._redis.expire(key, RULE_ACTION_STAGING_TTL)
        await self._redis.sadd(self.RULE_ACTION_EVENTS_KEY, event_code)

    async def pull_rule_actions(
        self, event_code: str, size: int
    ) -> list[dict[str, Any]]:
        key = f"rule_actions:{event_code}"
        raw = await self._redis.lpop(key, size)
        if raw is None:
            await self._redis.srem(self.RULE_ACTION_EVENTS_KEY, event_code)
            return []
        if isinstance(raw, bytes):
            return [orjson.loads(raw)]
        return [orjson.loads(item) for item in raw]

    async def list_staged_event_codes(self) -> list[str]:
        values = await self._redis.smembers(self.RULE_ACTION_EVENTS_KEY)
        return [v.decode() if isinstance(v, bytes) else str(v) for v in values]

    # ── Daily Limit Cache ────────────────────────────────

    DAILY_LIMIT_TTL = 86400  # 24 hours

    async def get_daily_count(
        self, account_id: uuid.UUID, event_code: str
    ) -> int | None:
        key = f"daily:{account_id}:{event_code}"
        val = await self._redis.get(key)
        return int(val) if val is not None else None

    async def set_daily_count(
        self, account_id: uuid.UUID, event_code: str, count: int
    ) -> None:
        key = f"daily:{account_id}:{event_code}"
        await self._redis.set(key, str(count), ex=self.DAILY_LIMIT_TTL)

    async def incr_daily_count(self, account_id: uuid.UUID, event_code: str) -> int:
        key = f"daily:{account_id}:{event_code}"
        new_val = await self._redis.incr(key)
        if new_val == 1:
            await self._redis.expire(key, self.DAILY_LIMIT_TTL)
        return new_val
