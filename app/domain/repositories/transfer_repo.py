"""Transaction repository interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from asyncpg import Connection

from app.domain.entities.idempotency_key import Transaction


class TransactionRepository(ABC):
    """Abstract repository for transaction (idempotency) operations."""

    @abstractmethod
    async def exists(self, idempotency_key: str, conn: Connection) -> bool:
        """Return True if the idempotency key has already been recorded."""
        ...

    @abstractmethod
    async def get_by_key(
        self, idempotency_key: str, conn: Connection
    ) -> Transaction | None:
        """Fetch a transaction by its idempotency key."""
        ...

    @abstractmethod
    async def get_by_id(self, tx_id: uuid.UUID, conn: Connection) -> Transaction | None:
        """Fetch a transaction by primary key."""
        ...

    @abstractmethod
    async def save(self, entry: Transaction, conn: Connection) -> None:
        """Insert a new transaction."""
        ...

    @abstractmethod
    async def save_many(self, entries: list[Transaction], conn: Connection) -> None:
        """Batch insert transactions."""
        ...

    @abstractmethod
    async def filter_existing(
        self, idempotency_keys: list[str], conn: Connection
    ) -> list[str]:
        """Return the subset of keys that already exist and are completed."""
        ...

    @abstractmethod
    async def mark_completed(self, idempotency_key: str, conn: Connection) -> None:
        """Mark transaction as completed."""
        ...

    @abstractmethod
    async def mark_failed(self, idempotency_key: str, conn: Connection) -> None:
        """Mark transaction as failed so it can be retried."""
        ...

    @abstractmethod
    async def delete_expired(self, conn: Connection) -> int:
        """Remove rows whose *expires_at* has passed. Returns count deleted."""
        ...
