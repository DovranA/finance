"""Request/response schemas for statistics endpoints."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class ClientStatsSummaryResponse(BaseModel):
    user_id: UUID
    period_days: int
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
    points: list[ClientTimelinePoint]


class ClientCategoryPoint(BaseModel):
    event_code: str | None = None
    description_i18n: dict[str, str] | None = None
    credits: int
    debits: int
    net: int
    transaction_count: int


class ClientStatsByCategoryResponse(BaseModel):
    user_id: UUID
    period_days: int
    categories: list[ClientCategoryPoint]


class ClientStatsStreaksResponse(BaseModel):
    user_id: UUID
    period_days: int
    current_streak_days: int
    longest_streak_days: int
    active_days_in_period: int
    last_active_day: date | None = None


class AdminSystemSummaryResponse(BaseModel):
    period_days: int
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


class PeriodQuery(BaseModel):
    period: str = Field(default="30d", pattern=r"^\d+d$")
