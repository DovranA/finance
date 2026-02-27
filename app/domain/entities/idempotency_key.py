"""Idempotency key domain entity."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class IdempotencyKey:
    """Represents a stored idempotency key to guarantee at-most-once processing.

    Once created, it is immutable — keys are never updated, only inserted and
    eventually expired/cleaned up.
    """

    id: uuid.UUID
    key: str
    status: str  # 'pending', 'completed', 'failed'
    response_code: int | None = None
    response_body: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        key: str,
        status: str = "pending",
        response_code: int | None = None,
        response_body: str | None = None,
        expires_at: datetime | None = None,
    ) -> IdempotencyKey:
        if not key:
            raise ValueError("Idempotency key must not be empty")
        return cls(
            id=uuid.uuid4(),
            key=key,
            status=status,
            response_code=response_code,
            response_body=response_body,
            expires_at=expires_at,
        )
