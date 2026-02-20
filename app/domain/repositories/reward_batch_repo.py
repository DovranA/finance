"""Reward batch repository interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from asyncpg import Connection

from app.domain.entities.reward_batch import RewardBatch


class RewardBatchRepository(ABC):

    @abstractmethod
    async def upsert_batch(
        self,
        content_id: uuid.UUID,
        publisher_id: uuid.UUID,
        action_code: str,
        publisher_reward: int,
        platform_fee: int,
        treasury_cut: int,
        conn: Connection,
    ) -> None:
        """Insert or update an unprocessed batch for the content + action."""
        ...

    @abstractmethod
    async def fetch_unprocessed_for_update(
        self, limit: int, conn: Connection
    ) -> list[RewardBatch]:
        """SELECT ... FOR UPDATE SKIP LOCKED unprocessed batches."""
        ...

    @abstractmethod
    async def mark_processed(
        self, batch_id: uuid.UUID, conn: Connection
    ) -> None:
        ...
