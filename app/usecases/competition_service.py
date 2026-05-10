"""Use case service for managing competition participation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from asyncpg import Pool

from app.core.logging import get_logger
from app.core.metrics import register_metrics
from app.core.config import get_settings
from app.domain.exceptions import CompetitionFrozen

if TYPE_CHECKING:
    from app.usecases.statistics import AdminStatisticsUseCase

logger = get_logger(__name__)


class CompetitionService:
    """Manages user competition participation based on messages."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def handle(
        self,
        user_id: uuid.UUID,
        in_competition: bool,
        admin_stats_uc: AdminStatisticsUseCase | None = None,
    ) -> None:
        """
        Add or remove user from competition table, capturing frozen rank and balance.

        Args:
            user_id: UUID of the user
            in_competition: True to add user to competition, False to remove
            admin_stats_uc: AdminStatisticsUseCase for calculating rank (required for joins)

        Raises:
            CompetitionFrozen: If trying to add user after freeze datetime
        """
        metrics = await register_metrics()

        # Check freeze datetime only when adding user to competition
        if in_competition:
            settings = get_settings()
            freeze_datetime = datetime.fromisoformat(
                settings.competition.freeze_datetime
            )
            current_time = datetime.utcnow()

            if current_time >= freeze_datetime:
                logger.warning(
                    "competition_frozen",
                    user_id=str(user_id),
                    freeze_datetime=settings.competition.freeze_datetime,
                    current_time=current_time.isoformat(),
                )
                metrics.inc_rabbitmq_message(
                    "competition-consumer", "competition", "frozen_rejection"
                )
                raise CompetitionFrozen(
                    f"Competition is frozen as of {settings.competition.freeze_datetime}"
                )

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
