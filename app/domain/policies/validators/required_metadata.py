"""Validates that required metadata keys are present."""

from __future__ import annotations

from typing import Any

from asyncpg import Connection

from app.domain.policies.base import ConditionValidator


class RequiredMetadataValidator(ConditionValidator):
    """Checks that all keys listed in ``required_metadata`` exist in metadata.

    Example condition::

        {"required_metadata": ["post_id"]}
    """

    key = "required_metadata"

    async def validate(
        self,
        value: Any,
        *,
        account: Any,
        metadata: dict[str, Any],
        conn: Connection,
    ) -> None:
        if not isinstance(value, list):
            return

        missing = [k for k in value if k not in metadata or metadata[k] is None]
        if missing:
            raise ValueError(f"Missing required metadata: {', '.join(missing)}")
