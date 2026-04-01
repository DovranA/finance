"""Base class for statistics use cases with shared logic."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from app.core.logging import get_logger
from app.domain.repositories.user_gateway import UserGateway

logger = get_logger(__name__)


class BaseStatisticsUseCase:
    """Base class for statistics use cases with shared user fetching logic."""

    def __init__(self, user_gateway: UserGateway) -> None:
        self._user_gateway = user_gateway

    async def _fetch_users_map(
        self,
        user_ids: list[uuid.UUID],
        current_user_id: Optional[uuid.UUID] = None,
        include_social_data: bool = False,
    ) -> dict[uuid.UUID, dict[str, Any]]:
        """
        Fetch users and return as a map for quick lookup.

        Args:
            user_ids: List of user IDs to fetch
            include_social_data: If True, include is_following and author_role

        Returns:
            Dictionary mapping user_id to user data
        """
        deduped_ids = list(dict.fromkeys(user_ids))
        if not deduped_ids:
            return {}

        try:
            users = await self._user_gateway.list_users_by_ids(
                current_user_id=current_user_id,
                user_ids=deduped_ids,
            )
        except Exception as exc:
            logger.warning(
                "user_lookup_unavailable_returning_without_profiles",
                error=str(exc),
                requested_users=len(deduped_ids),
            )
            return {}
        if include_social_data:
            return {
                user.id: {
                    "username": user.username,
                    "fullname": user.fullname,
                    "author_role": user.role,
                    "is_following": user.is_following,
                }
                for user in users
            }
        else:
            return {
                user.id: {
                    "username": user.username,
                    "fullname": user.fullname,
                    "role": user.role,
                }
                for user in users
            }
