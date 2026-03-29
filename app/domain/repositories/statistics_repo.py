"""Statistics repository interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import date
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
        start_from: date,
        end_to: date,
        direction: int | None,
        conn: Connection,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def get_admin_streaks(
        self,
        start_from: date,
        end_to: date,
        limit: int,
        direction: int | None,
        conn: Connection,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_admin_top_by_amount(
        self,
        start_from: date,
        end_to: date,
        limit: int,
        direction: int | None,
        conn: Connection,
    ) -> list[dict[str, Any]]: ...
