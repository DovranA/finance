from pydantic import BaseModel, Field


class SetTreasuryCurrencyRequest(BaseModel):
    new_balance: int = Field(ge=0)
    currency: str = Field(min_length=1)
