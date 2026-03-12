from __future__ import annotations

from typing import Any

from asyncpg import Connection

from app.domain.exceptions import DomainError
from app.domain.policies.base import ConditionValidator
from app.infrastructure.redis.cache import CacheService


class DailyLimitExceeded(DomainError):
    """Raised when the daily transaction limit has been exceeded."""


class DailyLimitValidator(ConditionValidator):
    key = "daily_limit"

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
        event_code = metadata["event_code"]

        # 1. Check Redis cache first
        if self._cache:
            count = await self._cache.get_daily_count(account.id, event_code)
            if count is not None:
                if count >= value:
                    raise DailyLimitExceeded("Daily limit exceeded")
                return

        # 2. Fallback to DB
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM ledger_entries le "
            "JOIN transactions t ON t.id = le.transaction_id "
            "WHERE le.account_id = $1 AND t.reference_type = $2 "
            "AND le.created_at >= CURRENT_DATE",
            account.id,
            event_code,
        )

        # Warm cache from DB count
        if self._cache:
            await self._cache.set_daily_count(account.id, event_code, count)

        if count >= value:
            raise DailyLimitExceeded("Daily limit exceeded")
