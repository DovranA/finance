"""Rule domain entity — event-driven rules stored in the DB."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# @dataclass
# class RuleCondition:
#     """Typed representation of a rule's conditions JSONB."""

#     min_balance: Optional[int] = None
#     role_required: Optional[list[str]] = None
#     one_time_only: Optional[bool] = None
#     daily_limit: Optional[int] = None
#     required_metadata: Optional[list[str]] = None
#     idempotency_pattern: Optional[str] = None


# @dataclass
# class RuleAction:
#     """Typed representation of a rule's actions JSONB."""

#     direction: int = 1  # 1 = credit, -1 = debit
#     amount: Optional[int] = None
#     reward: Optional[int] = None
#     currency: str = "TMT"


@dataclass
class Rule:
    """Configurable event-driven rule.

    Each rule maps an `event_code` (e.g. "official", "repost") to a set of
    conditions (validated by the ConditionEngine) and actions (direction,
    currency, reward amount, etc.).  Rules are stored in the `rules` table.
    """

    id: uuid.UUID
    event_code: str
    description: str | None
    conditions: dict[str, Any]
    actions: dict[str, Any]
    priority: int
    is_active: bool
    expired_at: datetime | None
    created_at: datetime
    updated_at: datetime

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
        description: str | None = None,
        priority: int = 0,
        expired_at: datetime | None = None,
    ) -> Rule:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid.uuid4(),
            event_code=event_code,
            description=description,
            conditions=conditions or {},
            actions=actions or {},
            priority=priority,
            is_active=True,
            expired_at=expired_at,
            created_at=now,
            updated_at=now,
        )
