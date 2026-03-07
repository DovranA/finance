"""Transaction domain entity — wraps the `transactions` table."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Transaction:
    """Represents a financial transaction with idempotency guarantees.

    Maps 1-to-1 with the `transactions` table.
    """

    id: uuid.UUID
    idempotency_key: str
    status: str  # 'pending', 'completed', 'failed'
    reference_type: str | None = None
    reference_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None

    @classmethod
    def generate_key(
        cls,
        event_id: uuid.UUID | None,
        account_id: uuid.UUID | None,
    ) -> str:
        if event_id and account_id:
            return f"{account_id}:{event_id}"
        return str(uuid.uuid4())

    @classmethod
    def create(
        cls,
        *,
        idempotency_key: str,
        status: str = "pending",
        reference_type: str | None = None,
        reference_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
    ) -> Transaction:
        if not idempotency_key:
            raise ValueError("Idempotency key must not be empty")
        return cls(
            id=uuid.uuid4(),
            idempotency_key=idempotency_key,
            status=status,
            reference_type=reference_type,
            reference_id=reference_id,
            metadata=metadata or {},
            expires_at=expires_at,
        )
