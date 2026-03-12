from __future__ import annotations

from typing import Any

from asyncpg import Connection

from app.domain.exceptions import DuplicateOperation
from app.domain.policies.base import ConditionValidator
from app.infrastructure.redis.cache import CacheService


class OneTimeValidator(ConditionValidator):
    key = "one_time_only"

    def __init__(self, cache: CacheService | None = None) -> None:
        self._cache = cache

    async def validate(
        self,
        value: Any,
        *,
        account: Any,
        metadata: dict[str, Any],
        conn: Connection,
    ) -> None:
        if not value:
            return

        # Use the resolved idempotency key from the rule pattern
        idem_key = metadata.get("idempotency_key", "")
        if not idem_key:
            return

        # 1. Check Redis cache first
        if self._cache:
            if await self._cache.is_one_time_done(account.id, idem_key):
                raise DuplicateOperation(f"one_time:{idem_key}")

        # 2. Fallback to DB — check by idempotency_key in transactions
        exists = await conn.fetchval(
            "SELECT 1 FROM transactions "
            "WHERE idempotency_key = $1 AND status = 'completed' LIMIT 1",
            idem_key,
        )

        if exists:
            if self._cache:
                await self._cache.mark_one_time_done(account.id, idem_key)
            raise DuplicateOperation(f"one_time:{idem_key}")
