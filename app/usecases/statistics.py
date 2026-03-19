"""Statistics use cases for client and admin endpoints."""

from __future__ import annotations

import re
import uuid
from typing import Literal

from asyncpg import Pool

from app.domain.repositories.account_repo import AccountRepository
from app.domain.repositories.statistics_repo import StatisticsRepository

_PERIOD_RE = re.compile(r"^(\d+)d$")


def parse_period_days(period: str) -> int:
    match = _PERIOD_RE.match(period or "")
    if not match:
        raise ValueError("period must be in Nd format, e.g. 7d or 30d")
    days = int(match.group(1))
    if days <= 0 or days > 3650:
        raise ValueError("period days must be between 1 and 3650")
    return days


def parse_direction(
    direction: Literal["credit", "debit"] | None,
) -> int | None:
    if direction is None:
        return None
    return 1 if direction == "credit" else -1


class ClientStatisticsUseCase:
    def __init__(
        self,
        pool: Pool,
        account_repo: AccountRepository,
        stats_repo: StatisticsRepository,
    ) -> None:
        self._pool = pool
        self._account_repo = account_repo
        self._stats_repo = stats_repo

    async def get_summary(
        self,
        *,
        user_id: uuid.UUID,
        period: str,
        direction: Literal["credit", "debit"] | None = None,
    ) -> dict:
        period_days = parse_period_days(period)
        direction_value = parse_direction(direction)
        async with self._pool.acquire() as conn:
            account = await self._account_repo.get_by_owner_id(user_id, conn)
            if account is None:
                return {
                    "user_id": user_id,
                    "period_days": period_days,
                    "found": False,
                    "total_credits": 0,
                    "total_debits": 0,
                    "net_change": 0,
                    "transaction_count": 0,
                    "avg_transaction_amount": 0,
                    "first_transaction_at": None,
                    "last_transaction_at": None,
                }

            summary = await self._stats_repo.get_client_summary(
                account.id, period_days, direction_value, conn
            )

        return {
            "user_id": user_id,
            "period_days": period_days,
            "found": True,
            "total_credits": int(summary.get("total_credits") or 0),
            "total_debits": int(summary.get("total_debits") or 0),
            "net_change": int(summary.get("net_change") or 0),
            "transaction_count": int(summary.get("transaction_count") or 0),
            "avg_transaction_amount": int(summary.get("avg_transaction_amount") or 0),
            "first_transaction_at": (
                summary.get("first_transaction_at").isoformat()
                if summary.get("first_transaction_at")
                else None
            ),
            "last_transaction_at": (
                summary.get("last_transaction_at").isoformat()
                if summary.get("last_transaction_at")
                else None
            ),
        }

    async def get_timeline(
        self,
        *,
        user_id: uuid.UUID,
        period: str,
        direction: Literal["credit", "debit"] | None = None,
    ) -> dict:
        period_days = parse_period_days(period)
        direction_value = parse_direction(direction)
        async with self._pool.acquire() as conn:
            account = await self._account_repo.get_by_owner_id(user_id, conn)
            if account is None:
                return {
                    "user_id": user_id,
                    "period_days": period_days,
                    "points": [],
                }
            points = await self._stats_repo.get_client_timeline(
                account.id, period_days, direction_value, conn
            )

        return {
            "user_id": user_id,
            "period_days": period_days,
            "points": points,
        }

    async def get_by_category(
        self,
        *,
        user_id: uuid.UUID,
        period: str,
        direction: Literal["credit", "debit"] | None = None,
    ) -> dict:
        period_days = parse_period_days(period)
        direction_value = parse_direction(direction)
        async with self._pool.acquire() as conn:
            account = await self._account_repo.get_by_owner_id(user_id, conn)
            if account is None:
                return {
                    "user_id": user_id,
                    "period_days": period_days,
                    "categories": [],
                }
            categories = await self._stats_repo.get_client_by_category(
                account.id, period_days, direction_value, conn
            )

        return {
            "user_id": user_id,
            "period_days": period_days,
            "categories": categories,
        }

    async def get_streaks(
        self,
        *,
        user_id: uuid.UUID,
        period: str,
        direction: Literal["credit", "debit"] | None = None,
    ) -> dict:
        period_days = parse_period_days(period)
        direction_value = parse_direction(direction)
        async with self._pool.acquire() as conn:
            account = await self._account_repo.get_by_owner_id(user_id, conn)
            if account is None:
                return {
                    "user_id": user_id,
                    "period_days": period_days,
                    "current_streak_days": 0,
                    "longest_streak_days": 0,
                    "active_days_in_period": 0,
                    "last_active_day": None,
                }
            streaks = await self._stats_repo.get_client_streaks(
                account.id, period_days, direction_value, conn
            )

        return {
            "user_id": user_id,
            "period_days": period_days,
            "current_streak_days": int(streaks.get("current_streak_days") or 0),
            "longest_streak_days": int(streaks.get("longest_streak_days") or 0),
            "active_days_in_period": int(streaks.get("active_days_in_period") or 0),
            "last_active_day": streaks.get("last_active_day"),
        }


class AdminStatisticsUseCase:
    def __init__(self, pool: Pool, stats_repo: StatisticsRepository) -> None:
        self._pool = pool
        self._stats_repo = stats_repo

    async def get_system_summary(
        self,
        *,
        period: str,
        direction: Literal["credit", "debit"] | None = None,
    ) -> dict:
        period_days = parse_period_days(period)
        direction_value = parse_direction(direction)
        async with self._pool.acquire() as conn:
            summary = await self._stats_repo.get_admin_system_summary(
                period_days,
                direction_value,
                conn,
            )

        return {
            "period_days": period_days,
            "total_users_with_accounts": int(
                summary.get("total_users_with_accounts") or 0
            ),
            "total_balance_in_system": int(summary.get("total_balance_in_system") or 0),
            "avg_user_balance": int(summary.get("avg_user_balance") or 0),
            "total_transactions": int(summary.get("total_transactions") or 0),
            "total_credits_distributed": int(
                summary.get("total_credits_distributed") or 0
            ),
            "total_debits_collected": int(summary.get("total_debits_collected") or 0),
        }

    async def get_streaks(
        self,
        *,
        period: str,
        limit: int,
        direction: Literal["credit", "debit"] | None = None,
    ) -> dict:
        period_days = parse_period_days(period)
        direction_value = parse_direction(direction)
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        async with self._pool.acquire() as conn:
            streaks = await self._stats_repo.get_admin_streaks(
                period_days,
                limit,
                direction_value,
                conn,
            )

        return {
            "period_days": period_days,
            "limit": limit,
            "streaks": streaks,
        }
