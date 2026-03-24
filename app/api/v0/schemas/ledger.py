"""Request/response schemas for ledger endpoints."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class CreateLedgerEntryRequest(BaseModel):
    """Request body for creating a ledger entry."""

    account_id: uuid.UUID
    amount: int = Field(..., gt=0, description="Amount in smallest currency unit")
    direction: int = Field(..., description="1 for credit, -1 for debit")
    transaction_id: uuid.UUID
