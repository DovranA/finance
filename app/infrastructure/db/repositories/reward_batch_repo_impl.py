"""Concrete reward batch repository — raw asyncpg SQL."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from asyncpg import Connection

from app.domain.entities.reward_batch import RewardBatch
from app.domain.repositories.reward_batch_repo import RewardBatchRepository


class PgRewardBatchRepository(RewardBatchRepository):

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
        """Insert or update (accumulate) an unprocessed batch.

        Uses INSERT ... ON CONFLICT to atomically accumulate counters.
        Conflict target: (content_id, action_code, is_processed) where is_processed = FALSE.
        """
        await conn.execute(
            """
            INSERT INTO reward_batches
                (id, content_id, publisher_id, action_code,
                 total_publisher_reward, total_platform_fee, total_treasury_cut,
                 action_count, is_processed, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 1, FALSE, NOW())
            ON CONFLICT (content_id, action_code, is_processed)
            WHERE is_processed = FALSE
            DO UPDATE SET
                total_publisher_reward = reward_batches.total_publisher_reward + EXCLUDED.total_publisher_reward,
                total_platform_fee = reward_batches.total_platform_fee + EXCLUDED.total_platform_fee,
                total_treasury_cut = reward_batches.total_treasury_cut + EXCLUDED.total_treasury_cut,
                action_count = reward_batches.action_count + 1
            """,
            uuid.uuid4(),
            content_id,
            publisher_id,
            action_code,
            publisher_reward,
            platform_fee,
            treasury_cut,
        )

    async def fetch_unprocessed_for_update(
        self, limit: int, conn: Connection
    ) -> list[RewardBatch]:
        rows = await conn.fetch(
            """
            SELECT id, content_id, publisher_id, action_code,
                   total_publisher_reward, total_platform_fee, total_treasury_cut,
                   action_count, is_processed, created_at, processed_at
            FROM reward_batches
            WHERE is_processed = FALSE
            ORDER BY created_at
            LIMIT $1
            FOR UPDATE SKIP LOCKED
            """,
            limit,
        )
        return [self._to_entity(r) for r in rows]

    async def mark_processed(
        self, batch_id: uuid.UUID, conn: Connection
    ) -> None:
        await conn.execute(
            "UPDATE reward_batches SET is_processed = TRUE, processed_at = $1 WHERE id = $2",
            datetime.now(timezone.utc),
            batch_id,
        )

    @staticmethod
    def _to_entity(row) -> RewardBatch:
        return RewardBatch(
            id=row["id"],
            content_id=row["content_id"],
            publisher_id=row["publisher_id"],
            action_code=row["action_code"],
            total_publisher_reward=row["total_publisher_reward"],
            total_platform_fee=row["total_platform_fee"],
            total_treasury_cut=row["total_treasury_cut"],
            action_count=row["action_count"],
            is_processed=row["is_processed"],
            created_at=row["created_at"],
            processed_at=row["processed_at"],
        )
