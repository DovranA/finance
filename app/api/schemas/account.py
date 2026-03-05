"""Request/response schemas for account endpoints."""

from pydantic import BaseModel


class BalanceResponse(BaseModel):
    user_id: str
    account_id: str | None = None
    balance: int
    currency: str
    found: bool
    cached: bool = False
