"""Gateway interface for user-management service lookups."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.domain.entities.user import User


class UserGateway(ABC):
    @abstractmethod
    async def list_users_by_ids(
        self,
        *,
        current_user_id: uuid.UUID,
        user_ids: list[uuid.UUID],
    ) -> list[User]:
        """Fetch users by ids from upstream user-management service."""
        ...
