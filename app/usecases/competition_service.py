"""Use case service for managing competition participation."""

from __future__ import annotations

import uuid

from asyncpg import Pool

from app.core.logging import get_logger
from app.core.metrics import register_metrics

logger = get_logger(__name__)


class CompetitionService:
    """Manages user competition participation based on messages."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def handle(self, user_id: uuid.UUID, in_competition: bool) -> None:
        """
        Add or remove user from competition table.

        Args:
            user_id: UUID of the user
            in_competition: True to add user to competition, False to remove
        """
        metrics = await register_metrics()

        async with self._pool.acquire() as conn:
            try:
                if in_competition:
                    await conn.execute(
                        "INSERT INTO competition (user_id, created_at) "
                        "VALUES ($1, NOW()) "
                        "ON CONFLICT (user_id) DO NOTHING",
                        user_id,
                    )
                    logger.info(
                        "user_added_to_competition",
                        user_id=str(user_id),
                    )
                    metrics.inc_rabbitmq_message(
                        "competition-consumer", "competition", "user_added"
                    )
                else:
                    result = await conn.execute(
                        "DELETE FROM competition WHERE user_id = $1",
                        user_id,
                    )
                    logger.info(
                        "user_removed_from_competition",
                        user_id=str(user_id),
                    )
                    metrics.inc_rabbitmq_message(
                        "competition-consumer", "competition", "user_removed"
                    )
            except Exception as e:
                logger.error(
                    "competition_operation_failed",
                    user_id=str(user_id),
                    in_competition=in_competition,
                    error=str(e),
                )
                metrics.inc_rabbitmq_message(
                    "competition-consumer", "competition", "operation_failed"
                )
                raise

    async def is_user_in_competition(self, user_id: uuid.UUID) -> bool:
        """Check if user is currently in competition."""
        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM competition WHERE user_id = $1)",
                user_id,
            )
            return result or False
