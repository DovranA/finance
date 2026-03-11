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

        event_id = str(metadata["event_id"])

        # 1. Check Redis cache first
        if self._cache:
            if await self._cache.is_one_time_done(account.id, event_id):
                raise DuplicateOperation(f"event:{event_id}")

        # 2. Fallback to DB
        exists = await conn.fetchval(
            "SELECT 1 FROM ledger_entries le "
            "JOIN transactions t ON t.id = le.transaction_id "
            "WHERE le.account_id = $1 AND t.reference_id = $2 LIMIT 1",
            account.id,
            event_id,
        )

        if exists:
            # Warm cache so next check skips DB
            if self._cache:
                await self._cache.mark_one_time_done(account.id, event_id)
            raise DuplicateOperation(f"event:{event_id}")
