from __future__ import annotations

from typing import Any

from asyncpg import Connection

from app.domain.exceptions import DomainError
from app.domain.policies.base import ConditionValidator


class CooldownDaysExceeded(DomainError):
    """Raised when an action is attempted before cooldown window ends."""


class CooldownDaysValidator(ConditionValidator):
    key = "cooldown_days"

    async def validate(
        self,
        value: Any,
        *,
        account: Any,
        metadata: dict[str, Any],
        conn: Connection,
    ) -> None:
        if value is None:
            return

        try:
            days = int(value)
        except (TypeError, ValueError):
            raise ValueError("cooldown_days must be an integer")

        if days <= 0:
            raise ValueError("cooldown_days must be greater than 0")

        event_code = metadata.get("event_code")
        if not event_code:
            raise ValueError("event_code is required for cooldown_days")

        exists = await conn.fetchval(
            "SELECT 1 FROM transactions "
            "WHERE reference_id = $1 "
            "AND reference_type = $2 "
            "AND status = 'completed' "
            "AND created_at >= NOW() - ($3 * INTERVAL '1 day') "
            "LIMIT 1",
            str(account.id),
            event_code,
            days,
        )

        if exists:
            raise CooldownDaysExceeded(
                f"cooldown_days:{days} not reached for event '{event_code}'"
            )
