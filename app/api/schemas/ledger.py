"""Request/response schemas for ledger endpoints."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class CreateLedgerEntryRequest(BaseModel):
    """Request body for creating a ledger entry."""

    account_id: uuid.UUID
    amount: int = Field(..., gt=0, description="Amount in smallest currency unit")
    entry_type: str = Field(..., description="'credit' or 'debit'")
    reference_id: uuid.UUID
    reference_type: str = Field(..., min_length=1, max_length=100)
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    currency: str = "TMT"
    metadata: dict | None = None
