"""Reward batch entity — aggregates rewards per content for publisher payout."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RewardBatch:
    """Aggregated reward batch per content piece.

    Accumulates counters and totals until batch processor picks them up.
    Uses FOR UPDATE SKIP LOCKED for concurrent-safe processing.
    """

    id: uuid.UUID
    content_id: uuid.UUID
    publisher_id: uuid.UUID
    action_code: str
    total_publisher_reward: int
    total_platform_fee: int
    total_treasury_cut: int
    action_count: int
    is_processed: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: datetime | None = None

    @classmethod
    def create(
        cls,
        content_id: uuid.UUID,
        publisher_id: uuid.UUID,
        action_code: str,
    ) -> RewardBatch:
        return cls(
            id=uuid.uuid4(),
            content_id=content_id,
            publisher_id=publisher_id,
            action_code=action_code,
            total_publisher_reward=0,
            total_platform_fee=0,
            total_treasury_cut=0,
            action_count=0,
            is_processed=False,
        )

    def add_action(
        self,
        publisher_reward: int,
        platform_fee: int,
        treasury_cut: int,
    ) -> None:
        self.total_publisher_reward += publisher_reward
        self.total_platform_fee += platform_fee
        self.total_treasury_cut += treasury_cut
        self.action_count += 1

    def mark_processed(self) -> None:
        self.is_processed = True
        self.processed_at = datetime.now(timezone.utc)
