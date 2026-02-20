"""Economic action repository interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from asyncpg import Connection

from app.domain.entities.economic_action import EconomicAction, EconomicActionVersion


class EconomicActionRepository(ABC):
    """Abstract repository for economic action CRUD + versioning."""

    @abstractmethod
    async def create_action(
        self, action: EconomicAction, conn: Connection
    ) -> None:
        ...

    @abstractmethod
    async def get_action_by_id(
        self, action_id: uuid.UUID, conn: Connection
    ) -> EconomicAction | None:
        ...

    @abstractmethod
    async def get_action_by_code(
        self, code: str, conn: Connection
    ) -> EconomicAction | None:
        ...

    @abstractmethod
    async def list_actions(self, conn: Connection) -> list[EconomicAction]:
        ...

    @abstractmethod
    async def set_active(
        self, action_id: uuid.UUID, is_active: bool, conn: Connection
    ) -> None:
        ...

    # ── Versions ──────────────────────────────────────────

    @abstractmethod
    async def create_version(
        self, version: EconomicActionVersion, conn: Connection
    ) -> None:
        ...

    @abstractmethod
    async def get_active_version(
        self, action_code: str, conn: Connection
    ) -> EconomicActionVersion | None:
        """Get the currently active config version for an action code."""
        ...

    @abstractmethod
    async def activate_version(
        self, version_id: uuid.UUID, action_id: uuid.UUID, conn: Connection
    ) -> None:
        """Deactivate all other versions for the action, activate this one."""
        ...

    @abstractmethod
    async def get_next_version_number(
        self, action_id: uuid.UUID, conn: Connection
    ) -> int:
        ...

    @abstractmethod
    async def list_versions(
        self, action_id: uuid.UUID, conn: Connection
    ) -> list[EconomicActionVersion]:
        ...
