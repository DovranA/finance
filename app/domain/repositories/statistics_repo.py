"""Statistics repository interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

from asyncpg import Connection


class StatisticsRepository(ABC):
    """Abstract repository for read-only statistics queries."""

    @abstractmethod
    async def get_client_summary(
        self,
        account_id: uuid.UUID,
        period_days: int,
        direction: int | None,
        conn: Connection,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def get_client_timeline(
        self,
        account_id: uuid.UUID,
        period_days: int,
        direction: int | None,
        conn: Connection,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_client_by_category(
        self,
        account_id: uuid.UUID,
        period_days: int,
        direction: int | None,
        conn: Connection,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_client_streaks(
        self,
        account_id: uuid.UUID,
        period_days: int,
        direction: int | None,
        conn: Connection,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def get_admin_system_summary(
        self,
        period_days: int,
        direction: int | None,
        conn: Connection,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def get_admin_streaks(
        self,
        period_days: int,
        limit: int,
        direction: int | None,
        conn: Connection,
    ) -> list[dict[str, Any]]: ...
