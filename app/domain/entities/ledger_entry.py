from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Direction constants matching DB CHECK constraint
DIRECTION_CREDIT = 1
DIRECTION_DEBIT = -1


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
    direction: int  # +1 or -1

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        *,
        account_id: uuid.UUID,
        transaction_id: uuid.UUID,
        amount: int,
        direction: int,
    ) -> LedgerEntry:
        if amount <= 0:
            raise ValueError("Ledger amount must be positive")
        if direction not in (DIRECTION_CREDIT, DIRECTION_DEBIT):
            raise ValueError(
                f"Direction must be {DIRECTION_CREDIT} or {DIRECTION_DEBIT}"
            )

        return cls(
            id=uuid.uuid4(),
            account_id=account_id,
            transaction_id=transaction_id,
            amount=amount,
            direction=direction,
        )
