"""Rule repository interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from asyncpg import Connection

from app.domain.entities.rule import Rule


class RuleRepository(ABC):
    """Abstract repository for Rule CRUD operations."""

    @abstractmethod
    async def get_by_id(self, rule_id: uuid.UUID, conn: Connection) -> Rule | None: ...

    @abstractmethod
    async def get_by_event_code(
        self, event_code: str, conn: Connection
    ) -> list[Rule]: ...

    @abstractmethod
    async def get_active_by_event_code(
        self, event_code: str, conn: Connection
    ) -> Rule | None: ...

    @abstractmethod
    async def list_all(
        self, conn: Connection, limit: int = 50, offset: int = 0
    ) -> list[Rule]: ...

    @abstractmethod
    async def count(self, conn: Connection) -> int: ...

    @abstractmethod
    async def create(self, rule: Rule, conn: Connection) -> None: ...

    @abstractmethod
    async def update(self, rule: Rule, conn: Connection) -> None: ...

    @abstractmethod
    async def delete(self, rule_id: uuid.UUID, conn: Connection) -> None: ...
