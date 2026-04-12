"""Statistics use cases for client and admin endpoints."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any, Literal, Optional

from asyncpg import Connection, Pool
import orjson

from app.core.logging import get_logger
from app.domain.entities.user import User
from app.domain.repositories.account_repo import AccountRepository
from app.domain.repositories.statistics_repo import StatisticsRepository
from app.domain.repositories.user_gateway import UserGateway
from app.infrastructure.redis.cache import CacheService
from app.usecases.statistics_base import BaseStatisticsUseCase

logger = get_logger(__name__)


def resolve_period_window(
    period: str,
    *,
    today: date | None = None,
) -> tuple[date, date]:
    normalized = (period or "").strip().lower()
    current_day = today or date.today()

    if normalized == "day":
        return current_day, current_day

    if normalized == "week":
        start_from = current_day - timedelta(days=(current_day.weekday() + 1) % 7)
        return start_from, start_from + timedelta(days=6)

    if normalized == "month":
        start_from = current_day.replace(day=1)
        if current_day.month == 12:
            next_month = date(current_day.year + 1, 1, 1)
        else:
            next_month = date(current_day.year, current_day.month + 1, 1)
        return start_from, next_month - timedelta(days=1)

    if normalized.endswith("d") and normalized[:-1].isdigit():
        days = int(normalized[:-1])
        if days <= 0 or days > 3650:
            raise ValueError("period days must be between 1 and 3650")
        start_from = current_day - timedelta(days=days - 1)
        return start_from, current_day

    raise ValueError("period must be one of: day, week, month (or Nd format like 7d)")


def parse_period_days(period: str, *, today: date | None = None) -> int:
    start_from, end_to = resolve_period_window(period, today=today)
    return (end_to - start_from).days + 1


def parse_direction(
    direction: Literal["credit", "debit"] | None,
) -> int | None:
    if direction is None:
        return None
    return 1 if direction == "credit" else -1


def _validate_page_limit(page: int, limit: int) -> None:
    if page <= 0:
        raise ValueError("page must be greater than 0")
    if limit <= 0 or limit > 100:
        raise ValueError("limit must be between 1 and 100")


def _build_page_info(*, total_count: int, page: int, limit: int) -> dict:
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
    return {
        "has_next_page": page < total_pages,
        "has_previous_page": page > 1 and total_pages > 0,
        "total_pages": total_pages,
        "page": page,
        "limit": limit,
    }


def _paginate_items(*, items: list[dict], page: int, limit: int) -> dict:
    total_count = len(items)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    data = items[start_idx:end_idx] if start_idx < total_count else []
    return {
        "data": data,
        "page_info": _build_page_info(total_count=total_count, page=page, limit=limit),
    }


def _validate_date_range(start_from: date, end_to: date) -> None:
    if start_from > end_to:
        raise ValueError("start_from must be less than or equal to end_to")


def _window_days(start_from: date, end_to: date) -> int:
    return (end_to - start_from).days + 1


def _paginate_window_without_count(*, items: list[dict], page: int, limit: int) -> dict:
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    data = items[start_idx:end_idx]
    has_next_page = len(items) > end_idx
    return {
        "data": data,
        "page_info": {
            "has_next_page": has_next_page,
            "has_previous_page": page > 1,
            "total_pages": 0,
            "page": page,
            "limit": limit,
        },
    }


class ClientStatisticsUseCase(BaseStatisticsUseCase):
    def __init__(
        self,
        pool: Pool,
        account_repo: AccountRepository,
        user_gateway: UserGateway,
        stats_repo: StatisticsRepository,
        cache: CacheService | None = None,
    ) -> None:
        super().__init__(user_gateway)
        self._pool = pool
        self._stats_repo = stats_repo
        self._account_repo = account_repo
        self._cache = cache

    async def _get_token_account(
        self,
        user_id: uuid.UUID,
        conn: Connection,
    ):
        accounts = await self._account_repo.list_by_owner_id(user_id, conn)
        return next((a for a in accounts if a.currency.upper() == "TOKEN"), None)

    async def get_summary(
        self,
        *,
        user_id: uuid.UUID,
        period: str,
        direction: Literal["credit", "debit"] | None = None,
    ) -> dict:
        start_from, end_to = resolve_period_window(period)
        period_days = _window_days(start_from, end_to)
        direction_value = parse_direction(direction)
        async with self._pool.acquire() as conn:
            account = await self._get_token_account(user_id, conn)
            if account is None:
                return {
                    "user_id": user_id,
                    "period_days": period_days,
                    "period_start": start_from,
                    "period_end": end_to,
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
                account.id,
                start_from,
                end_to,
                direction_value,
                conn,
            )

        return {
            "user_id": user_id,
            "period_days": period_days,
            "period_start": start_from,
            "period_end": end_to,
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
        page: int = 1,
        limit: int = 20,
        direction: Literal["credit", "debit"] | None = None,
    ) -> dict:
        start_from, end_to = resolve_period_window(period)
        period_days = _window_days(start_from, end_to)
        _validate_page_limit(page, limit)
        direction_value = parse_direction(direction)
        async with self._pool.acquire() as conn:
            account = await self._get_token_account(user_id, conn)
            if account is None:
                points = []
            else:
                points = await self._stats_repo.get_client_timeline(
                    account.id,
                    start_from,
                    end_to,
                    direction_value,
                    conn,
                )

        normalized_points = [
            {
                "day": p.get("day"),
                "credits": int(p.get("credits") or 0),
                "debits": int(p.get("debits") or 0),
                "net": int(p.get("net") or 0),
                "transaction_count": int(p.get("transaction_count") or 0),
            }
            for p in points
        ]

        return _paginate_items(items=normalized_points, page=page, limit=limit)

    async def get_by_category(
        self,
        *,
        user_id: uuid.UUID,
        period: str,
        page: int = 1,
        limit: int = 20,
        direction: Literal["credit", "debit"] | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        start_from, end_to = resolve_period_window(period)
        _validate_page_limit(page, limit)
        direction_value = parse_direction(direction)
        async with self._pool.acquire() as conn:
            accounts = await self._account_repo.list_by_owner_id(user_id, conn)
            if not accounts:
                categories = []
            else:
                categories = []
                for account in accounts:
                    categories.extend(
                        await self._stats_repo.get_client_by_category(
                            account.id,
                            start_from,
                            end_to,
                            direction_value,
                            conn,
                            tags=tags,
                        )
                    )

        aggregated_categories: dict[
            tuple[str | None, str | None, int | None, str | None], dict
        ] = {}
        for c in categories:
            description_i18n = c.get("description_i18n")
            if isinstance(description_i18n, str):
                description_i18n = orjson.loads(description_i18n)
            if not isinstance(description_i18n, dict):
                description_i18n = {}

            key = (
                c.get("rule_id"),
                c.get("event_code") or c.get("category"),
                c.get("direction"),
                c.get("currency"),
            )
            if key not in aggregated_categories:
                aggregated_categories[key] = {
                    "rule_id": c.get("rule_id"),
                    "event_code": c.get("event_code") or c.get("category"),
                    "description_i18n": description_i18n,
                    "tags": list(c.get("tags") or []),
                    "direction": c.get("direction"),
                    "currency": c.get("currency"),
                    "amount": 0,
                    "transaction_count": 0,
                }

            aggregated_categories[key]["amount"] += int(c.get("amount") or 0)
            aggregated_categories[key]["transaction_count"] += int(
                c.get("transaction_count") or 0
            )

        normalized_categories = []
        for c in aggregated_categories.values():

            normalized_categories.append(
                {
                    "rule_id": c.get("rule_id"),
                    "event_code": c.get("event_code") or c.get("category"),
                    "description_i18n": c.get("description_i18n") or {},
                    "tags": list(c.get("tags") or []),
                    "direction": c.get("direction"),
                    "currency": c.get("currency"),
                    "amount": int(c.get("amount") or 0),
                    "transaction_count": int(c.get("transaction_count") or 0),
                }
            )

        normalized_categories.sort(
            key=lambda item: (
                -int(item.get("amount") or 0),
                str(item.get("rule_id") or ""),
            )
        )

        return _paginate_items(items=normalized_categories, page=page, limit=limit)

    async def get_streaks(
        self,
        *,
        user_id: uuid.UUID,
        period: str,
        page: int = 1,
        limit: int = 20,
        direction: Literal["credit", "debit"] | None = None,
    ) -> dict:
        start_from, end_to = resolve_period_window(period)
        period_days = _window_days(start_from, end_to)
        _validate_page_limit(page, limit)

        direction_value = parse_direction(direction)
        async with self._pool.acquire() as conn:
            account = await self._get_token_account(user_id, conn)
            if account is None:
                payload = {
                    "user_id": user_id,
                    "period_days": period_days,
                    "current_streak_days": 0,
                    "longest_streak_days": 0,
                    "active_days_in_period": 0,
                    "last_active_day": None,
                }
                items: list[dict] = []
            else:
                streaks = await self._stats_repo.get_client_streaks(
                    account.id,
                    start_from,
                    end_to,
                    direction_value,
                    conn,
                )
                payload = {
                    "user_id": user_id,
                    "period_days": period_days,
                    "current_streak_days": int(streaks.get("current_streak_days") or 0),
                    "longest_streak_days": int(streaks.get("longest_streak_days") or 0),
                    "active_days_in_period": int(
                        streaks.get("active_days_in_period") or 0
                    ),
                    "last_active_day": streaks.get("last_active_day"),
                }
                items = [payload]

        return _paginate_items(items=items, page=page, limit=limit)

    async def get_top_by_amount(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        current_user_id: Optional[uuid.UUID] = None,
        currency: str = "TOKEN",
    ) -> dict:
        _validate_page_limit(page, limit)
        offset = (page - 1) * limit

        total_count = 0
        normalized_rows: list[dict[str, Any]] = []
        previous_payload: dict[str, Any] | None = None
        from_cache = False

        if self._cache is not None:
            cached_payload = await self._cache.get_cached_top_by_amount_page(
                page=page,
                limit=limit,
                currency=currency,
            )
            if cached_payload is not None:
                total_count = int(cached_payload.get("total_count") or 0)
                normalized_rows = list(cached_payload.get("rows") or [])
                from_cache = True
            else:
                previous_payload = (
                    await self._cache.get_cached_top_by_amount_previous_page(
                        page=page,
                        limit=limit,
                        currency=currency,
                    )
                )

        async with self._pool.acquire() as conn:
            my_rank = None
            if current_user_id is not None:
                my_rank = await self._stats_repo.get_admin_top_by_amount_rank(
                    conn,
                    current_user_id,
                    currency,
                )
            if not from_cache:
                total_count = await self._stats_repo.get_admin_top_by_amount_count(
                    conn,
                    currency,
                )
                rows = await self._stats_repo.get_admin_top_by_amount(
                    conn,
                    limit,
                    offset,
                    currency,
                )

                # Extract user IDs for batch lookup
                user_ids = [row.get("user_id") for row in rows]
                users_map = await self._fetch_users_map(
                    user_ids, current_user_id, include_social_data=True
                )
                normalized_rows = [
                    {
                        "user_id": str(row.get("user_id")),
                        "username": users_map.get(row.get("user_id"), {}).get(
                            "username"
                        ),
                        "fullname": users_map.get(row.get("user_id"), {}).get(
                            "fullname"
                        ),
                        "author_role": users_map.get(row.get("user_id"), {}).get(
                            "author_role"
                        ),
                        "is_following": (
                            users_map.get(row.get("user_id"), {}).get("is_following")
                            if current_user_id
                            else None
                        ),
                        "total_amount": int(row.get("total_amount") or 0),
                    }
                    for row in rows
                ]

        # Keep place status stable during TOP_BY_AMOUNT_CACHE_TTL.
        # Recompute only when cache is rebuilt.
        if from_cache:
            for idx, row in enumerate(normalized_rows, start=1):
                current_rank = int(row.get("current_rank") or (offset + idx))
                row["current_rank"] = current_rank
                row["previous_rank"] = row.get("previous_rank", current_rank)
                row["place_change"] = row.get("place_change", "stay")
        else:
            previous_rows = list((previous_payload or {}).get("rows") or [])
            previous_rank_by_user: dict[str, int] = {}
            for prev_idx, prev_row in enumerate(previous_rows, start=1):
                prev_user_id = str(prev_row.get("user_id") or "")
                if not prev_user_id:
                    continue
                prev_rank = int(prev_row.get("current_rank") or (offset + prev_idx))
                previous_rank_by_user[prev_user_id] = prev_rank

            for idx, row in enumerate(normalized_rows, start=1):
                current_rank = offset + idx
                previous_rank = previous_rank_by_user.get(str(row.get("user_id") or ""))

                if previous_rank is None:
                    place_change = "stay"
                    previous_rank = current_rank
                elif current_rank < previous_rank:
                    place_change = "increased"
                elif current_rank > previous_rank:
                    place_change = "decreased"
                else:
                    place_change = "stay"

                row["current_rank"] = current_rank
                row["previous_rank"] = previous_rank
                row["place_change"] = place_change

        if self._cache is not None and not from_cache:
            payload = {
                "total_count": total_count,
                "rows": normalized_rows,
            }
            await self._cache.set_cached_top_by_amount_page(
                page=page,
                limit=limit,
                currency=currency,
                payload=payload,
            )
            await self._cache.set_cached_top_by_amount_previous_page(
                page=page,
                limit=limit,
                currency=currency,
                payload=payload,
            )

        return {
            "data": normalized_rows or [],
            "page_info": _build_page_info(
                total_count=total_count,
                page=page,
                limit=limit,
            ),
            "my_rank": my_rank,
            "total_participants": total_count,
            "cached": from_cache,
        }


class AdminStatisticsUseCase(BaseStatisticsUseCase):
    def __init__(
        self,
        pool: Pool,
        stats_repo: StatisticsRepository,
        user_gateway: UserGateway,
        cache: CacheService | None = None,
    ) -> None:
        super().__init__(user_gateway)
        self._pool = pool
        self._stats_repo = stats_repo
        self._cache = cache

    async def get_system_summary(
        self,
        *,
        start_from: date,
        end_to: date,
        direction: Literal["credit", "debit"] | None = None,
    ) -> dict:
        _validate_date_range(start_from, end_to)
        direction_value = parse_direction(direction)
        async with self._pool.acquire() as conn:
            summary = await self._stats_repo.get_admin_system_summary(
                start_from,
                end_to,
                direction_value,
                conn,
            )

        return {
            "start_from": start_from,
            "end_to": end_to,
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
        start_from: date,
        end_to: date,
        page: int = 1,
        limit: int,
        direction: Literal["credit", "debit"] | None = None,
    ) -> dict:
        _validate_date_range(start_from, end_to)
        direction_value = parse_direction(direction)
        _validate_page_limit(page, limit)

        window_end = page * limit
        fetch_limit = window_end + 1

        async with self._pool.acquire() as conn:
            streaks = await self._stats_repo.get_admin_streaks(
                start_from,
                end_to,
                fetch_limit,
                direction_value,
                conn,
            )

        # Extract user IDs for batch lookup
        user_ids = [row.get("user_id") for row in streaks]
        users_map = await self._fetch_users_map(
            user_ids, None, include_social_data=False
        )

        normalized_streaks = [
            {
                "user_id": row.get("user_id"),
                "username": users_map.get(row.get("user_id"), {}).get("username"),
                "fullname": users_map.get(row.get("user_id"), {}).get("fullname"),
                "current_streak_days": int(row.get("current_streak_days") or 0),
                "longest_streak_days": int(row.get("longest_streak_days") or 0),
                "active_days_in_period": int(row.get("active_days_in_period") or 0),
                "last_active_day": row.get("last_active_day"),
            }
            for row in streaks
        ]
        return _paginate_window_without_count(
            items=normalized_streaks,
            page=page,
            limit=limit,
        )

    async def get_top_by_amount(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        current_user_id: Optional[uuid.UUID] = None,
        currency: str = "TOKEN",
    ) -> dict:
        _validate_page_limit(page, limit)
        offset = (page - 1) * limit

        async with self._pool.acquire() as conn:
            total_count = await self._stats_repo.get_admin_top_by_amount_count(
                conn,
                currency,
            )
            my_rank = None
            if current_user_id is not None:
                my_rank = await self._stats_repo.get_admin_top_by_amount_rank(
                    conn,
                    current_user_id,
                    currency,
                )
            rows = await self._stats_repo.get_admin_top_by_amount(
                conn,
                limit,
                offset,
                currency,
            )
        # Extract user IDs for batch lookup
        user_ids = [row.get("user_id") for row in rows]
        users_map = await self._fetch_users_map(user_ids, include_social_data=True)
        normalized_rows = [
            {
                "user_id": str(row.get("user_id")),
                "username": users_map.get(row.get("user_id"), {}).get("username"),
                "fullname": users_map.get(row.get("user_id"), {}).get("fullname"),
                "author_role": users_map.get(row.get("user_id"), {}).get("author_role"),
                "is_following": (
                    users_map.get(row.get("user_od"), {}).get("is_following")
                    if current_user_id
                    else None
                ),
                "total_amount": int(row.get("total_amount") or 0),
            }
            for row in rows
        ]
        return {
            "data": normalized_rows or [],
            "page_info": _build_page_info(
                total_count=total_count,
                page=page,
                limit=limit,
            ),
            "my_rank": my_rank,
            "total_participants": total_count,
            "cached": False,
        }
