"""Request/response schemas for account endpoints."""

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
