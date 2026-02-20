"""Processed event repository interface — idempotency."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from asyncpg import Connection


class ProcessedEventRepository(ABC):

    @abstractmethod
    async def exists(self, event_id: uuid.UUID, conn: Connection) -> bool:
        """Check if event was already processed."""
        ...

    @abstractmethod
    async def mark_processed(
        self, event_id: uuid.UUID, event_type: str, conn: Connection
    ) -> None:
        """Record that event has been processed."""
        ...
