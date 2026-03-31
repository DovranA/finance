"""Account REST API endpoints."""

import uuid

from fastapi import APIRouter, Body, Depends
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from app.api.v0.auth import get_current_user_id
from app.api.v0.schemas.account import (
    BalanceResponse,
    NewBalanceRequest,
    BatchNewBalanceRequest,
    BatchSetBalanceResponse,
)
from app.usecases.get_balance import GetBalanceUseCase
from app.usecases.set_balance import SetBalanceUseCase
from app.usecases.set_balance_batch import BatchSetBalanceUseCase

router = APIRouter(prefix="/accounts", tags=["Accounts"], route_class=DishkaRoute)


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    uc: FromDishka[GetBalanceUseCase],
    user_id: uuid.UUID = Depends(get_current_user_id),
    currency: str | None = None,
) -> BalanceResponse:
    """Get the balance for a user account."""
    result = await uc.execute(user_id=user_id, currency=currency)
    return BalanceResponse(**result)


@router.get("/{user_id}/balance", response_model=BalanceResponse)
async def get_balance(
    user_id: uuid.UUID,
    uc: FromDishka[GetBalanceUseCase],
    currency: str | None = None,
) -> BalanceResponse:
    """Get the balance for a user account."""
    result = await uc.execute(user_id=user_id, currency=currency)
    return BalanceResponse(**result)


@router.post("/{user_id}/new_balance", response_model=BalanceResponse)
async def set_new_balance(
    user_id: uuid.UUID,
    uc: FromDishka[SetBalanceUseCase],
    data: NewBalanceRequest = Body(...),
) -> BalanceResponse:
    """Get the balance for a user account."""
    result = await uc.execute(
        user_id=user_id,
        new_balance=data.new_balance,
        currency=data.currency,
    )
    return BalanceResponse(**result)


@router.post("/new_balance/batch", response_model=BatchSetBalanceResponse)
async def set_new_balance_batch(
    uc: FromDishka[BatchSetBalanceUseCase],
    data: BatchNewBalanceRequest = Body(...),
) -> BatchSetBalanceResponse:
    payload = [item.model_dump() for item in data.items]
    result = await uc.execute(items=payload)
    return BatchSetBalanceResponse(**result)
