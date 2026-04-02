from __future__ import annotations

from typing import Any

from asyncpg import Connection

from app.domain.exceptions import DomainError
from app.domain.policies.base import ConditionValidator


class RoleNotAllowed(DomainError):
    """Raised when the account metadata does not match the required role."""


class RoleRequiredValidator(ConditionValidator):
    key = "role_required"

    async def validate(
        self,
        value: Any,
        *,
        account: Any,
        metadata: dict[str, Any],
        conn: Connection,
    ) -> None:
        account_role = metadata.get("role", "simple")
        if account_role not in value:
            raise RoleNotAllowed(f"Role '{account_role}' not in allowed roles: {value}")
