"""Account domain entity."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Account:
    """User financial account.

    Balance is stored as BIGINT (smallest currency unit).
    All mutations must happen inside a DB transaction with row-level locking.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    balance: int
    currency: str = "USD"
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def credit(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError(f"Credit amount must be positive, got {amount}")
        self.balance += amount
        self.updated_at = datetime.now(timezone.utc)

    def debit(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError(f"Debit amount must be positive, got {amount}")
        if self.balance < amount:
            raise ValueError(
                f"Insufficient balance: {self.balance} < {amount}"
            )
        self.balance -= amount
        self.updated_at = datetime.now(timezone.utc)

    @classmethod
    def create(cls, user_id: uuid.UUID, currency: str = "USD") -> Account:
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            balance=0,
            currency=currency,
        )
