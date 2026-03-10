from __future__ import annotations

from typing import Any

from asyncpg import Connection

from app.domain.policies.registry import ValidatorRegistry


class ConditionEngine:
    """Evaluates a set of conditions against registered validators."""

    def __init__(self, registry: ValidatorRegistry) -> None:
        self.registry = registry

    async def validate(
        self,
        conditions: dict[str, Any],
        *,
        account: Any,
        metadata: dict[str, Any],
        conn: Connection,
    ) -> None:
        if not conditions:
            return

        for key, value in conditions.items():
            validator = self.registry.get(key)
            print(key, value)
            if not validator:
                raise ValueError(f"Unknown condition: {key}")

            await validator.validate(
                value,
                account=account,
                metadata=metadata,
                conn=conn,
            )
