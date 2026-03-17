"""Domain event types produced by RabbitMQ mapping pipeline."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InboxEvent:
    """Single inbox-ready event derived from incoming transport payload."""

    event_id: uuid.UUID
    event_code: str
    user_id: uuid.UUID
    role: str | None
    metadata: dict[str, Any]
