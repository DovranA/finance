from __future__ import annotations

from typing import Any

from asyncpg import Connection

from app.domain.exceptions import DomainError
from app.domain.policies.base import ConditionValidator


class DailyLimitExceeded(DomainError):
    """Raised when the daily transaction limit has been exceeded."""


class DailyLimitValidator(ConditionValidator):
    key = "daily_limit"

    async def validate(
        self,
        value: Any,
        *,
        account: Any,
        metadata: dict[str, Any],
        conn: Connection,
    ) -> None:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM ledger_entries "
            "WHERE account_id = $1 AND entry_type = $2 AND created_at >= CURRENT_DATE",
            account.id,
            metadata["event_code"],
        )

        if count >= value:
            raise DailyLimitExceeded("Daily limit exceeded")
