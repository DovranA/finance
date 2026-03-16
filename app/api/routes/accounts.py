"""Account REST API endpoints."""

import uuid

from fastapi import APIRouter, Body
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
async def set_new_balance(
    user_id: uuid.UUID,
    uc: FromDishka[SetBalanceUseCase],
    data: NewBalanceRequest = Body(...),
) -> BalanceResponse:
    """Get the balance for a user account."""
    result = await uc.execute(user_id=user_id, new_balance=data.new_balance)
    return BalanceResponse(**result)
