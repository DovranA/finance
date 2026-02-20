"""Account REST API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.dependencies import get_balance_uc
from app.api.schemas.schemas import BalanceResponse
from app.usecases.get_balance import GetBalanceUseCase

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("/{user_id}/balance", response_model=BalanceResponse)
async def get_balance(
    user_id: uuid.UUID,
    uc: GetBalanceUseCase = Depends(get_balance_uc),
):
    """Get the balance for a user account."""
    result = await uc.execute(user_id=user_id)
    return BalanceResponse(**result)
