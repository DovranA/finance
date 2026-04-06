"""Rule domain entity — event-driven rules stored in the DB."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Rule:
    """Configurable event-driven rule.

    Each rule maps an `event_code` (e.g. "official", "repost") to a set of
    conditions (validated by the ConditionEngine) and actions (direction,
    currency, reward amount, etc.).  Rules are stored in the `rules` table.
    """

    id: uuid.UUID
    event_code: str
    description_i18n: dict[str, str] | None
    conditions: dict[str, Any]
    actions: dict[str, Any]
    priority: int
    is_active: bool
    expired_at: datetime | None
    created_at: datetime
    updated_at: datetime
    tags: list[str] = field(default_factory=list)

    # ── Convenience helpers ──────────────────────────────────

    @property
    def is_expired(self) -> bool:
        if self.expired_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expired_at

    @property
    def is_usable(self) -> bool:
        return self.is_active and not self.is_expired

    @classmethod
    def create(
        cls,
        *,
        event_code: str,
        conditions: dict[str, Any] | None = None,
        actions: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        description_i18n: dict[str, str] | None = None,
        priority: int = 0,
        expired_at: datetime | None = None,
    ) -> Rule:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid.uuid4(),
            event_code=event_code,
            description_i18n=description_i18n,
            conditions=conditions or {},
            actions=actions or {},
            tags=tags or [],
            priority=priority,
            is_active=True,
            expired_at=expired_at,
            created_at=now,
            updated_at=now,
        )
