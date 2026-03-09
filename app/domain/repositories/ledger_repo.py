"""Ledger repository interface — append-only."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from asyncpg import Connection

from app.domain.entities.ledger_entry import LedgerEntry


class LedgerRepository(ABC):
    """Abstract repository for immutable ledger operations."""

    @abstractmethod
    async def insert(self, entry: LedgerEntry, conn: Connection) -> None:
        """Insert a new ledger entry. No updates or deletes allowed."""
        ...

    @abstractmethod
    async def insert_many(self, entries: list[LedgerEntry], conn: Connection) -> None:
        """Insert a new ledger list entries. No updates or deletes allowed."""
        ...

    @abstractmethod
    async def get_by_account(
        self,
        account_id: uuid.UUID,
        conn: Connection,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LedgerEntry]: ...

    @abstractmethod
    async def get_by_transaction(
        self, transaction_id: uuid.UUID, conn: Connection
    ) -> list[LedgerEntry]: ...
