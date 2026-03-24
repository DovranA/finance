"""Statistics endpoints for client and admin."""

from uuid import UUID
from typing import Literal

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Header, HTTPException, Query

from app.api.schemas.statistics import (
    AdminTopByAmountResponse,
    AdminStreaksResponse,
    AdminSystemSummaryResponse,
    ClientStatsByCategoryResponse,
    ClientStatsStreaksResponse,
    ClientStatsSummaryResponse,
    ClientStatsTimelineResponse,
)
from app.usecases.statistics import AdminStatisticsUseCase, ClientStatisticsUseCase


client_router = APIRouter(
    prefix="/accounts",
    tags=["Statistics"],
    route_class=DishkaRoute,
)

admin_router = APIRouter(
    prefix="/admin/statistics",
    tags=["Admin Statistics"],
    route_class=DishkaRoute,
)


def _ensure_admin_role(x_role: str | None) -> None:
    if (x_role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="admin role required")


@client_router.get(
    "/{user_id}/statistics/summary",
    response_model=ClientStatsSummaryResponse,
)
async def client_summary(
    user_id: UUID,
    uc: FromDishka[ClientStatisticsUseCase],
    period: str = Query("30d", pattern=r"^\d+d$"),
    direction: Literal["credit", "debit"] | None = Query(None),
) -> ClientStatsSummaryResponse:
    result = await uc.get_summary(user_id=user_id, period=period, direction=direction)
    return ClientStatsSummaryResponse(**result)


@client_router.get(
    "/{user_id}/statistics/timeline",
    response_model=ClientStatsTimelineResponse,
)
async def client_timeline(
    user_id: UUID,
    uc: FromDishka[ClientStatisticsUseCase],
    period: str = Query("30d", pattern=r"^\d+d$"),
    direction: Literal["credit", "debit"] | None = Query(None),
) -> ClientStatsTimelineResponse:
    result = await uc.get_timeline(
        user_id=user_id,
        period=period,
        direction=direction,
    )
    return ClientStatsTimelineResponse(**result)


@client_router.get(
    "/{user_id}/statistics/by-category",
    response_model=ClientStatsByCategoryResponse,
)
async def client_by_category(
    user_id: UUID,
    uc: FromDishka[ClientStatisticsUseCase],
    period: str = Query("30d", pattern=r"^\d+d$"),
    direction: Literal["credit", "debit"] | None = Query(None),
) -> ClientStatsByCategoryResponse:
    result = await uc.get_by_category(
        user_id=user_id,
        period=period,
        direction=direction,
    )
    return ClientStatsByCategoryResponse(**result)


@client_router.get(
    "/{user_id}/statistics/streaks",
    response_model=ClientStatsStreaksResponse,
)
async def client_streaks(
    user_id: UUID,
    uc: FromDishka[ClientStatisticsUseCase],
    period: str = Query("30d", pattern=r"^\d+d$"),
    direction: Literal["credit", "debit"] | None = Query(None),
) -> ClientStatsStreaksResponse:
    result = await uc.get_streaks(
        user_id=user_id,
        period=period,
        direction=direction,
    )
    return ClientStatsStreaksResponse(**result)


@admin_router.get(
    "/system/summary",
    response_model=AdminSystemSummaryResponse,
)
async def admin_system_summary(
    uc: FromDishka[AdminStatisticsUseCase],
    period: str = Query("30d", pattern=r"^\d+d$"),
    direction: Literal["credit", "debit"] | None = Query(None),
    x_role: str | None = Header(None, alias="x-role"),
) -> AdminSystemSummaryResponse:
    _ensure_admin_role(x_role)
    result = await uc.get_system_summary(period=period, direction=direction)
    return AdminSystemSummaryResponse(**result)


@admin_router.get(
    "/streaks",
    response_model=AdminStreaksResponse,
)
async def admin_streaks(
    uc: FromDishka[AdminStatisticsUseCase],
    period: str = Query("30d", pattern=r"^\d+d$"),
    limit: int = Query(20, ge=1, le=100),
    direction: Literal["credit", "debit"] | None = Query(None),
    x_role: str | None = Header(None, alias="x-role"),
) -> AdminStreaksResponse:
    _ensure_admin_role(x_role)
    result = await uc.get_streaks(period=period, limit=limit, direction=direction)
    return AdminStreaksResponse(**result)


@admin_router.get(
    "/top-by-amount",
    response_model=AdminTopByAmountResponse,
)
async def admin_top_by_amount(
    uc: FromDishka[AdminStatisticsUseCase],
    limit: int = Query(20, ge=1, le=100),
    direction: Literal["credit", "debit"] | None = Query(None),
    x_role: str | None = Header(None, alias="x-role"),
) -> AdminTopByAmountResponse:
    _ensure_admin_role(x_role)
    result = await uc.get_top_by_amount(
        limit=limit,
        direction=direction,
    )
    return AdminTopByAmountResponse(**result)
