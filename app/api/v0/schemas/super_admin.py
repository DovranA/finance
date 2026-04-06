import uuid

from pydantic import BaseModel, Field


class SetTreasuryCurrencyRequest(BaseModel):
    new_balance: int = Field(ge=0)
    currency: str = Field(min_length=1)


class OfficialRequestActionResponse(BaseModel):
    request_id: uuid.UUID
    idempotency_key: str
    status: str
    user_id: str | None = None
    amount: int | None = None
    currency: str
    event_code: str | None = None
    approval_required: bool = True
