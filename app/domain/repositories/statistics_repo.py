"""Statistics repository interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any

from asyncpg import Connection


class StatisticsRepository(ABC):
    """Abstract repository for read-only statistics queries."""

    @abstractmethod
    async def get_client_summary(
        self,
        account_id: uuid.UUID,
        start_from: date,
        end_to: date,
        direction: int | None,
        conn: Connection,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def get_client_timeline(
        self,
        account_id: uuid.UUID,
        start_from: date,
        end_to: date,
        direction: int | None,
        conn: Connection,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_client_by_category(
        self,
        account_id: uuid.UUID,
        start_from: date,
        end_to: date,
        direction: int | None,
        conn: Connection,
        tags: list[str] | None = None,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_client_streaks(
        self,
        account_id: uuid.UUID,
        start_from: date,
        end_to: date,
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
        conn: Connection,
        limit: int,
        offset: int,
        currency: str,
        order_by_frozen: bool = False,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_admin_top_by_amount_count(
        self,
        conn: Connection,
        currency: str,
    ) -> int: ...

    @abstractmethod
    async def get_admin_top_by_amount_rank(
        self,
        conn: Connection,
        user_id: uuid.UUID,
        currency: str,
        order_by_frozen: bool = False,
    ) -> int | None: ...

    @abstractmethod
    async def freeze_competition_snapshot(
        self,
        conn: Connection,
        currency: str,
    ) -> int: ...

    @abstractmethod
    async def competition_snapshot_needs_refresh(
        self,
        conn: Connection,
        freeze_datetime: datetime,
    ) -> bool: ...

    @abstractmethod
    async def get_admin_top_by_amount_previous_ranks(
        self,
        conn: Connection,
        user_ids: list[uuid.UUID],
        currency: str,
        comparison_from: datetime,
    ) -> dict[uuid.UUID, int]: ...
