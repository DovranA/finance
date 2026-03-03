"""Account REST API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from app.api.schemas.account import BalanceResponse
from app.usecases.get_balance import GetBalanceUseCase

router = APIRouter(prefix="/accounts", tags=["Accounts"], route_class=DishkaRoute)


@router.get("/{user_id}/balance", response_model=BalanceResponse)
async def get_balance(
    user_id: uuid.UUID,
    uc: FromDishka[GetBalanceUseCase],
) -> BalanceResponse:
    """Get the balance for a user account."""
    result = await uc.execute(user_id=user_id)
    return BalanceResponse(**result)
