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
    DeleteAccountResponse,
    UpdateIsActiveRequest,
)
from app.usecases.delete_account import DeleteAccountUseCase
from app.usecases.get_balance import GetBalanceUseCase
from app.usecases.set_balance import SetBalanceUseCase
from app.usecases.set_balance_batch import BatchSetBalanceUseCase
from app.usecases.user_crud import UpdateIsActiveUserUseCase

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


@router.post("/{user_id}/is_blocked", status_code=201)
async def update_is_blocked(
    user_id: uuid.UUID,
    data: UpdateIsActiveRequest,
    uc: FromDishka[UpdateIsActiveUserUseCase],
):
    return await uc.execute(user_id=user_id, is_blocked=data.is_blocked)


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


@router.delete("", response_model=DeleteAccountResponse)
async def delete_my_accounts(
    uc: FromDishka[DeleteAccountUseCase],
    user_id: uuid.UUID = Depends(get_current_user_id),
    hard_delete: bool = False,
) -> DeleteAccountResponse:
    result = await uc.execute(user_id=user_id, hard_delete=hard_delete)
    return DeleteAccountResponse(**result)


@router.delete("/{user_id}", response_model=DeleteAccountResponse)
async def delete_accounts_by_user_id(
    user_id: uuid.UUID,
    uc: FromDishka[DeleteAccountUseCase],
    hard_delete: bool = False,
) -> DeleteAccountResponse:
    result = await uc.execute(user_id=user_id, hard_delete=hard_delete)
    return DeleteAccountResponse(**result)
