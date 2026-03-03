from abc import ABC, abstractmethod
from typing import Any

from asyncpg import Connection


class ConditionValidator(ABC):
    """Base class for condition validators used in policy evaluation."""

    key: str  # JSON key name this validator handles

    @abstractmethod
    async def validate(
        self,
        value: Any,
        *,
        account: Any,
        metadata: dict[str, Any],
        conn: Connection,
    ) -> None:
        """Validate a condition. Raise on violation."""
        ...
