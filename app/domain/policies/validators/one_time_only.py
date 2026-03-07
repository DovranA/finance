from __future__ import annotations

from typing import Any

from asyncpg import Connection

from app.domain.exceptions import DuplicateOperation
from app.domain.policies.base import ConditionValidator


class OneTimeValidator(ConditionValidator):
    key = "one_time_only"

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

        exists = await conn.fetchval(
            "SELECT 1 FROM ledger_entries le "
            "JOIN transactions t ON t.id = le.transaction_id "
            "WHERE le.account_id = $1 AND t.reference_id = $2 LIMIT 1",
            account.id,
            str(metadata["event_id"]),
        )

        if exists:
            raise DuplicateOperation(f"event:{metadata['event_id']}")
