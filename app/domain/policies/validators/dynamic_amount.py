from typing import Any

from asyncpg import Connection

from app.domain.policies.base import ConditionValidator


class DynamicAmountValidator(ConditionValidator):
    key = "dynamic_amount"

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
        if not isinstance(value, bool):
            raise ValueError("dynamic_amount will be only bool")
        dynamic_amount = metadata.get("dynamic_amount", "")
        if not dynamic_amount:
            raise ValueError("missed dynamic amount on metadata")
