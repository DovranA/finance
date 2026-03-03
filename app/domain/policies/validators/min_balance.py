from __future__ import annotations

from typing import Any

from asyncpg import Connection

from app.domain.exceptions import InsufficientFunds
from app.domain.policies.base import ConditionValidator


class MinBalanceValidator(ConditionValidator):
    key = "min_balance"

    async def validate(
        self,
        value: Any,
        *,
        account: Any,
        metadata: dict[str, Any],
        conn: Connection,
    ) -> None:
        if account.balance < value:
            raise InsufficientFunds(account.id, value)
