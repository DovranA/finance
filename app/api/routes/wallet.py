from __future__ import annotations

import uuid

from fastapi import APIRouter
from dishka.integrations.fastapi import FromDishka, DishkaRoute

from app.api.schemas.account import BalanceResponse
from app.usecases.get_balance import GetBalanceUseCase

router = APIRouter(prefix="/wallet", tags=["Wallet"], route_class=DishkaRoute)


@router.post("wallet/balance")
async def wallet_balance():
    pass
