from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class LedgerEntryType(StrEnum):
    """Ledger-level entry direction: credit or debit."""

    CREDIT = "credit"
    DEBIT = "debit"


@dataclass(frozen=True)
class LedgerEntry:
    """Immutable ledger entry (append-only)."""

    id: uuid.UUID
    account_id: uuid.UUID
    amount: int
    entry_type: LedgerEntryType
    currency: str

    reference_id: uuid.UUID
    reference_type: str

    idempotency_key: str
    metadata: dict[str, Any]

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        *,
        account_id: uuid.UUID,
        amount: int,
        entry_type: LedgerEntryType,
        reference_id: uuid.UUID,
        reference_type: str,
        idempotency_key: str,
        currency: str = "TMT",
        metadata: dict[str, Any] | None = None,
    ) -> "LedgerEntry":
        if amount <= 0:
            raise ValueError("Ledger amount must be positive")

        return cls(
            id=uuid.uuid4(),
            account_id=account_id,
            amount=amount,
            entry_type=entry_type,
            currency=currency,
            reference_id=reference_id,
            reference_type=reference_type,
            idempotency_key=idempotency_key,
            metadata=metadata or {},
        )
