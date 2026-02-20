"""Actor action entity — records an individual user action."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class ActorAction:
    """Records a single user action (like, share, view, etc.) with its
    computed reward based on the economic config version at the time."""

    id: uuid.UUID
    actor_id: uuid.UUID
    content_id: uuid.UUID
    action_code: str
    economic_version_id: uuid.UUID
    reward_amount: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        actor_id: uuid.UUID,
        content_id: uuid.UUID,
        action_code: str,
        economic_version_id: uuid.UUID,
        reward_amount: int,
    ) -> ActorAction:
        return cls(
            id=uuid.uuid4(),
            actor_id=actor_id,
            content_id=content_id,
            action_code=action_code,
            economic_version_id=economic_version_id,
            reward_amount=reward_amount,
        )
