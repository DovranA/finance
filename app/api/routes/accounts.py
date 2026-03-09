"""Account REST API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from app.api.schemas.account import BalanceResponse, NewBalanceRequest
from app.usecases.get_balance import GetBalanceUseCase
from app.usecases.set_balance import SetBalanceUseCase

router = APIRouter(prefix="/accounts", tags=["Accounts"], route_class=DishkaRoute)


@router.get("/{user_id}/balance", response_model=BalanceResponse)
async def get_balance(
    user_id: uuid.UUID,
    uc: FromDishka[GetBalanceUseCase],
) -> BalanceResponse:
    """Get the balance for a user account."""
    result = await uc.execute(user_id=user_id)
    return BalanceResponse(**result)


@router.post("/{user_id}/new_balance", response_model=BalanceResponse)
async def get_balance(
    user_id: uuid.UUID,
    data: NewBalanceRequest,
    uc: FromDishka[SetBalanceUseCase],
) -> BalanceResponse:
    """Get the balance for a user account."""
    result = await uc.execute(user_id=user_id, new_balance=data.new_balance)
    return BalanceResponse(**result)
