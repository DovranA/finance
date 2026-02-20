"""Economic action and version entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class EconomicAction:
    """Dynamic economic action definition (e.g. LIKE, SHARE, VIEW)."""

    id: uuid.UUID
    code: str
    description: str
    is_active: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(cls, code: str, description: str = "") -> EconomicAction:
        return cls(
            id=uuid.uuid4(),
            code=code.upper(),
            description=description,
            is_active=True,
        )


@dataclass
class EconomicActionVersion:
    """Versioned reward configuration for an economic action.

    All monetary fields are BIGINT (smallest currency unit).
    Changing version must not affect already-processed events.
    """

    id: uuid.UUID
    action_id: uuid.UUID
    publisher_reward: int
    actor_reward: int
    platform_fee: int
    treasury_cut: int
    version: int
    is_active: bool
    active_from: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        action_id: uuid.UUID,
        publisher_reward: int,
        actor_reward: int,
        platform_fee: int,
        treasury_cut: int,
        version: int,
    ) -> EconomicActionVersion:
        return cls(
            id=uuid.uuid4(),
            action_id=action_id,
            publisher_reward=publisher_reward,
            actor_reward=actor_reward,
            platform_fee=platform_fee,
            treasury_cut=treasury_cut,
            version=version,
            is_active=False,
            active_from=datetime.now(timezone.utc),
        )

    @property
    def total_cost(self) -> int:
        """Total cost per action = all reward components combined."""
        return (
            self.publisher_reward
            + self.actor_reward
            + self.platform_fee
            + self.treasury_cut
        )
