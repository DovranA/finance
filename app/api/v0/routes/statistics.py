"""Statistics endpoints for client and admin."""

from datetime import date
from uuid import UUID
from typing import Literal

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Header, HTTPException, Query

from app.api.v0.schemas.statistics import (
    AdminStreaksPaginatedResponse,
    AdminTopByAmountResponse,
    AdminTopByAmountPaginatedResponse,
    AdminSystemSummaryResponse,
    ClientStatsByCategoryPaginatedResponse,
    ClientStatsByCategoryResponse,
    ClientStatsStreaksPaginatedResponse,
    ClientStatsSummaryResponse,
    ClientStatsTimelinePaginatedResponse,
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
    response_model=ClientStatsTimelinePaginatedResponse,
)
async def client_timeline(
    user_id: UUID,
    uc: FromDishka[ClientStatisticsUseCase],
    period: str = Query("30d", pattern=r"^\d+d$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    direction: Literal["credit", "debit"] | None = Query(None),
) -> ClientStatsTimelinePaginatedResponse:
    result = await uc.get_timeline(
        user_id=user_id,
        period=period,
        page=page,
        limit=limit,
        direction=direction,
    )
    return ClientStatsTimelinePaginatedResponse(**result)


@client_router.get(
    "/{user_id}/statistics/by-category",
    response_model=ClientStatsByCategoryPaginatedResponse,
)
async def client_by_category(
    user_id: UUID,
    uc: FromDishka[ClientStatisticsUseCase],
    period: str = Query("30d", pattern=r"^\d+d$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    direction: Literal["credit", "debit"] | None = Query(None),
) -> ClientStatsByCategoryPaginatedResponse:
    result = await uc.get_by_category(
        user_id=user_id,
        period=period,
        page=page,
        limit=limit,
        direction=direction,
    )
    return ClientStatsByCategoryPaginatedResponse(**result)


@client_router.get(
    "/{user_id}/statistics/streaks",
    response_model=ClientStatsStreaksPaginatedResponse,
)
async def client_streaks(
    user_id: UUID,
    uc: FromDishka[ClientStatisticsUseCase],
    period: str = Query("30d", pattern=r"^\d+d$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    direction: Literal["credit", "debit"] | None = Query(None),
) -> ClientStatsStreaksPaginatedResponse:
    result = await uc.get_streaks(
        user_id=user_id,
        period=period,
        page=page,
        limit=limit,
        direction=direction,
    )
    return ClientStatsStreaksPaginatedResponse(**result)


@admin_router.get(
    "/system/summary",
    response_model=AdminSystemSummaryResponse,
)
async def admin_system_summary(
    uc: FromDishka[AdminStatisticsUseCase],
    start_from: date = Query(...),
    end_to: date = Query(...),
    direction: Literal["credit", "debit"] | None = Query(None),
) -> AdminSystemSummaryResponse:
    result = await uc.get_system_summary(
        start_from=start_from,
        end_to=end_to,
        direction=direction,
    )
    return AdminSystemSummaryResponse(**result)


@admin_router.get(
    "/streaks",
    response_model=AdminStreaksPaginatedResponse,
)
async def admin_streaks(
    uc: FromDishka[AdminStatisticsUseCase],
    start_from: date = Query(...),
    end_to: date = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    direction: Literal["credit", "debit"] | None = Query(None),
) -> AdminStreaksPaginatedResponse:
    result = await uc.get_streaks(
        start_from=start_from,
        end_to=end_to,
        page=page,
        limit=limit,
        direction=direction,
    )
    return AdminStreaksPaginatedResponse(**result)


@admin_router.get(
    "/top-by-amount",
    response_model=AdminTopByAmountPaginatedResponse,
)
async def admin_top_by_amount(
    uc: FromDishka[AdminStatisticsUseCase],
    start_from: date = Query(...),
    end_to: date = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    direction: Literal["credit", "debit"] | None = Query(None),
) -> AdminTopByAmountPaginatedResponse:

    result = await uc.get_top_by_amount(
        start_from=start_from,
        end_to=end_to,
        page=page,
        limit=limit,
        direction=direction,
    )
    return AdminTopByAmountPaginatedResponse(**result)
