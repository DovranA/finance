from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.domain.value_objects.enums import LedgerDirection

# Direction constants matching DB CHECK constraint


@dataclass(frozen=True)
class LedgerEntry:
    """Immutable ledger entry (append-only).

    `direction` is +1 (credit) or -1 (debit), stored as SMALLINT.
    `transaction_id` links back to the `transactions` table.
    """

    id: uuid.UUID
    account_id: uuid.UUID
    transaction_id: uuid.UUID
    amount: int
    direction: LedgerDirection  # +1 or -1

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        *,
        account_id: uuid.UUID,
        transaction_id: uuid.UUID,
        amount: int,
        direction: LedgerDirection,
    ) -> LedgerEntry:
        if amount <= 0:
            raise ValueError("Ledger amount must be positive")
        if not isinstance(direction, LedgerDirection):
            raise ValueError(
                f"Direction must be {LedgerDirection.DIRECTION_CREDIT} or {LedgerDirection.DIRECTION_DEBIT}"
            )

        return cls(
            id=uuid.uuid4(),
            account_id=account_id,
            transaction_id=transaction_id,
            amount=amount,
            direction=direction,
        )
