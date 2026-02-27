"""Idempotency key repository interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from asyncpg import Connection

from app.domain.entities.idempotency_key import IdempotencyKey


class IdempotencyRepository(ABC):
    """Abstract repository for idempotency-key operations."""

    @abstractmethod
    async def exists(self, key: str, conn: Connection) -> bool:
        """Return True if *key* has already been recorded."""
        ...

    @abstractmethod
    async def get_by_key(self, key: str, conn: Connection) -> IdempotencyKey | None:
        """Fetch a stored idempotency record by its key string."""
        ...

    @abstractmethod
    async def save(self, entry: IdempotencyKey, conn: Connection) -> None:
        """Persist a new idempotency key record."""
        ...

    @abstractmethod
    async def mark_completed(
        self,
        key: str,
        response_code: int,
        response_body: str,
        conn: Connection,
    ) -> None:
        """Mark an existing key as completed with its cached response."""
        ...

    @abstractmethod
    async def mark_failed(self, key: str, conn: Connection) -> None:
        """Mark an existing key as failed so it can be retried."""
        ...

    @abstractmethod
    async def delete_expired(self, conn: Connection) -> int:
        """Remove rows whose *expires_at* has passed. Returns count deleted."""
        ...
