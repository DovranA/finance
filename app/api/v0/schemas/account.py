"""Request/response schemas for account endpoints."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class CurrencyBalanceItem(BaseModel):
    account_id: str
    currency: str
    balance: int
    cached: bool = False


class BalanceResponse(BaseModel):
    user_id: str
    found: bool
    cached: bool = False
    balances: list[CurrencyBalanceItem] = Field(default_factory=list)


class NewBalanceRequest(BaseModel):
    new_balance: int = Field(ge=1)
    currency: str


class BatchNewBalanceItem(BaseModel):
    user_id: uuid.UUID
    new_balance: int = Field(ge=1)
    currency: str


class BatchNewBalanceRequest(BaseModel):
    items: list[BatchNewBalanceItem] = Field(min_length=1)


class BatchSetBalanceResult(BaseModel):
    user_id: str
    new_balance: int
    currency: str
    account_existed: bool | None = None
    success: bool
    error: str | None = None
    balances: list[CurrencyBalanceItem] = Field(default_factory=list)


class BatchSetBalanceResponse(BaseModel):
    total: int
    success: int
    failed: int
    results: list[BatchSetBalanceResult]
