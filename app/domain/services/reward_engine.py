"""Reward engine domain service — core business logic for reward calculations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.entities.actor_action import ActorAction
from app.domain.entities.economic_action import EconomicActionVersion
from app.domain.entities.ledger_entry import LedgerEntry
from app.domain.value_objects.enums import EntryType


@dataclass(frozen=True)
class RewardCalculation:
    """Result of calculating rewards for a single action."""

    actor_action: ActorAction
    actor_ledger_entry: LedgerEntry | None
    publisher_reward: int
    platform_fee: int
    treasury_cut: int


class RewardEngine:
    """Stateless domain service for reward calculations.

    Uses the active economic config version to compute rewards
    for an actor action. Does NOT perform any I/O.
    """

    @staticmethod
    def calculate(
        actor_id: uuid.UUID,
        content_id: uuid.UUID,
        action_code: str,
        config: EconomicActionVersion,
        actor_account_id: uuid.UUID,
    ) -> RewardCalculation:
        """Calculate all reward components for a single action.

        Returns:
            RewardCalculation with actor_action, optional ledger entry, and
            the publisher/platform/treasury amounts for batch aggregation.
        """
        actor_action = ActorAction.create(
            actor_id=actor_id,
            content_id=content_id,
            action_code=action_code,
            economic_version_id=config.id,
            reward_amount=config.actor_reward,
        )

        actor_ledger_entry: LedgerEntry | None = None
        if config.actor_reward > 0:
            actor_ledger_entry = LedgerEntry.create(
                account_id=actor_account_id,
                amount=config.actor_reward,
                entry_type=EntryType.ACTOR_REWARD,
                reference_id=actor_action.id,
                metadata={
                    "action_code": action_code,
                    "content_id": str(content_id),
                    "economic_version": config.version,
                },
            )

        return RewardCalculation(
            actor_action=actor_action,
            actor_ledger_entry=actor_ledger_entry,
            publisher_reward=config.publisher_reward,
            platform_fee=config.platform_fee,
            treasury_cut=config.treasury_cut,
        )
