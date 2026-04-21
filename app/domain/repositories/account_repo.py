"""Account repository interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from asyncpg import Connection

from app.domain.entities.account import Account
from app.domain.value_objects.enums import AccountTypes


class AccountRepository(ABC):
    """Abstract repository for Account operations."""

    @abstractmethod
    async def get_by_id(
        self, account_id: uuid.UUID, conn: Connection
    ) -> Account | None: ...
    @abstractmethod
    async def get_by_account_type(
        self, type: AccountTypes, conn: Connection, currency: str = "TOKEN"
    ) -> Account | None: ...

    @abstractmethod
    async def get_by_owner_id(
        self, user_id: uuid.UUID, conn: Connection, currency: str | None = None
    ) -> Account | None: ...
    @abstractmethod
    async def list_by_owner_id(
        self, user_id: uuid.UUID, conn: Connection
    ) -> list[Account]: ...
    @abstractmethod
    async def list_by_owner_ids(
        self, user_ids: list[uuid.UUID], conn: Connection
    ) -> list[Account]: ...
    @abstractmethod
    async def get_by_owner_id_for_update(
        self, user_id: uuid.UUID, conn: Connection, currency: str | None = None
    ) -> Account | None: ...

    @abstractmethod
    async def get_for_update(
        self, account_id: uuid.UUID, conn: Connection
    ) -> Account | None:
        """Lock the row with SELECT ... FOR UPDATE."""
        ...

    @abstractmethod
    async def get_or_create_by_owner_id(
        self, user_id: uuid.UUID, conn: Connection, currency: str = "TOKEN"
    ) -> Account: ...

    @abstractmethod
    async def update_balance(
        self, account_id: uuid.UUID, new_balance: int, conn: Connection
    ) -> None: ...

    @abstractmethod
    async def debit(self, account_id: uuid.UUID, amount: int, conn: Connection) -> None:
        """Decrease balance by amount."""
        ...

    @abstractmethod
    async def credit(
        self, account_id: uuid.UUID, amount: int, conn: Connection
    ) -> None:
        """Increase balance by amount."""
        ...

    @abstractmethod
    async def create(self, account: Account, conn: Connection) -> None: ...

    @abstractmethod
    async def update_is_active(
        self, user_id: uuid.UUID, is_active: bool, conn: Connection
    ) -> None: ...
