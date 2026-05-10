"""Request/response schemas for statistics endpoints."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.api.v0.schemas.general import PaginatedResponse


class ClientStatsSummaryResponse(BaseModel):
    user_id: UUID
    period_days: int
    period_start: date
    period_end: date
    found: bool
    total_credits: int
    total_debits: int
    net_change: int
    transaction_count: int
    avg_transaction_amount: int
    first_transaction_at: str | None = None
    last_transaction_at: str | None = None


class ClientTimelinePoint(BaseModel):
    day: date
    credits: int
    debits: int
    net: int
    transaction_count: int


class ClientStatsTimelineResponse(BaseModel):
    user_id: UUID
    period_days: int
    period_start: date
    period_end: date
    points: list[ClientTimelinePoint]


class ClientStatsTimelinePaginatedResponse(
    PaginatedResponse[list[ClientTimelinePoint]]
):
    pass


class ClientCategoryPoint(BaseModel):
    rule_id: str | None = None
    event_code: str | None = None
    description_i18n: dict[str, str] | None = None
    tags: list[str] = Field(default_factory=list)
    direction: int | None = None
    currency: str | None = None
    amount: int
    transaction_count: int


class ClientStatsByCategoryResponse(BaseModel):
    user_id: UUID
    period_days: int
    period_start: date
    period_end: date
    categories: list[ClientCategoryPoint]


class ClientStatsByCategoryPaginatedResponse(
    PaginatedResponse[list[ClientCategoryPoint]]
):
    pass


class ClientStatsStreaksResponse(BaseModel):
    user_id: UUID
    period_days: int
    period_start: date
    period_end: date
    current_streak_days: int
    longest_streak_days: int
    active_days_in_period: int
    last_active_day: date | None = None


class ClientStatsStreaksPaginatedResponse(
    PaginatedResponse[list[ClientStatsStreaksResponse]]
):
    pass


class AdminSystemSummaryResponse(BaseModel):
    start_from: date
    end_to: date
    total_users_with_accounts: int
    total_balance_in_system: int
    avg_user_balance: int
    total_transactions: int
    total_credits_distributed: int
    total_debits_collected: int


class AdminStreakPoint(BaseModel):
    user_id: UUID
    current_streak_days: int
    longest_streak_days: int
    active_days_in_period: int
    last_active_day: date | None = None


class AdminStreaksResponse(BaseModel):
    period_days: int
    limit: int
    streaks: list[AdminStreakPoint]


class AdminStreaksPaginatedResponse(PaginatedResponse[list[AdminStreakPoint]]):
    pass


class AdminTopByAmountPoint(BaseModel):
    user_id: UUID
    total_amount: int
    frozen_rank: int | None = None
    frozen_balance: int | None = None


class AdminTopByAmountResponse(BaseModel):
    limit: int
    direction: str
    cached: bool
    items: list[AdminTopByAmountPoint]


class AdminTopByAmountPaginatedResponse(PaginatedResponse[list[AdminTopByAmountPoint]]):
    direction: str
    cached: bool


class PeriodQuery(BaseModel):
    period: str = Field(default="30d", pattern=r"^\d+d$")
