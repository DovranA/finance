"""Outbox message entity — Transactional Outbox Pattern."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class OutboxMessage:
    """Represents a domain event to be published to RabbitMQ.

    Written inside the same DB transaction as business data to guarantee
    atomicity. A relay worker polls pending messages and publishes them.
    """

    id: uuid.UUID
    aggregate_type: str
    aggregate_id: uuid.UUID
    event_type: str          # used as routing key
    payload: dict[str, Any]
    status: str = "pending"  # pending | sent | failed
    retry_count: int = 0
    max_retries: int = 5
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: datetime | None = None

    @classmethod
    def create(
        cls,
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        event_type: str,
        payload: dict[str, Any],
    ) -> OutboxMessage:
        return cls(
            id=uuid.uuid4(),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
        )

    def mark_sent(self) -> None:
        self.status = "sent"
        self.sent_at = datetime.now(timezone.utc)

    def mark_failed(self) -> None:
        self.retry_count += 1
        if self.retry_count >= self.max_retries:
            self.status = "failed"
