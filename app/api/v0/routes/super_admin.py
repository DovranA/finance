from dishka import FromDishka
from fastapi import APIRouter
from dishka.integrations.fastapi import DishkaRoute

from app.api.v0.schemas.super_admin import SetTreasuryCurrencyRequest
from app.usecases.superadmin import SuperAdminUseCase

router = APIRouter(prefix="/super-admin", tags=["Super Admin"], route_class=DishkaRoute)


@router.post("/treasury")
async def set_treasury(
    data: SetTreasuryCurrencyRequest, uc: FromDishka[SuperAdminUseCase]
):
    return await uc.set_treasury(data.new_balance, data.currency)


@router.get("/treasury/{currency}")
async def get_treasury(currency: str, uc: FromDishka[SuperAdminUseCase]):
    return await uc.get_treasury(currency)
