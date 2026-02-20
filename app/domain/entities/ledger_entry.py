"""Immutable ledger entry entity."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class LedgerEntry:
    """Immutable financial ledger entry.

    Once created, a ledger entry MUST NOT be modified or deleted.
    Positive amount = credit, negative amount = debit.
    """

    id: uuid.UUID
    account_id: uuid.UUID
    amount: int
    currency: str
    entry_type: str
    reference_id: uuid.UUID
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        account_id: uuid.UUID,
        amount: int,
        entry_type: str,
        reference_id: uuid.UUID,
        currency: str = "USD",
        metadata: dict[str, Any] | None = None,
    ) -> LedgerEntry:
        return cls(
            id=uuid.uuid4(),
            account_id=account_id,
            amount=amount,
            currency=currency,
            entry_type=entry_type,
            reference_id=reference_id,
            metadata=metadata or {},
        )
