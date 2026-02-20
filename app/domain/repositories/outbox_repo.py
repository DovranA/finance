"""Outbox repository interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from asyncpg import Connection

from app.domain.entities.outbox_message import OutboxMessage


class OutboxRepository(ABC):

    @abstractmethod
    async def insert(self, message: OutboxMessage, conn: Connection) -> None:
        """Insert an outbox message inside the current transaction."""
        ...

    @abstractmethod
    async def fetch_pending(
        self, limit: int, conn: Connection
    ) -> list[OutboxMessage]:
        """Fetch unsent messages FOR UPDATE SKIP LOCKED."""
        ...

    @abstractmethod
    async def mark_sent(
        self, message_id: uuid.UUID, conn: Connection
    ) -> None:
        ...

    @abstractmethod
    async def mark_failed(
        self, message_id: uuid.UUID, retry_count: int, conn: Connection
    ) -> None:
        ...

    @abstractmethod
    async def delete_sent_older_than(
        self, days: int, conn: Connection
    ) -> int:
        """Cleanup old sent messages. Returns count deleted."""
        ...
