"""Concrete statistics repository with aggregate SQL queries."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from asyncpg import Connection

from app.domain.repositories.statistics_repo import StatisticsRepository


class PgStatisticsRepository(StatisticsRepository):
    async def get_client_summary(
        self,
        account_id: uuid.UUID,
        period_days: int,
        direction: int | None,
        conn: Connection,
    ) -> dict[str, Any]:
        row = await conn.fetchrow(
            """
            SELECT
                COALESCE(SUM(CASE WHEN le.direction = 1 THEN le.amount ELSE 0 END), 0) AS total_credits,
                COALESCE(SUM(CASE WHEN le.direction = -1 THEN le.amount ELSE 0 END), 0) AS total_debits,
                COALESCE(SUM(CASE WHEN le.direction = 1 THEN le.amount ELSE -le.amount END), 0) AS net_change,
                COALESCE(COUNT(DISTINCT le.transaction_id), 0) AS transaction_count,
                COALESCE(AVG(le.amount), 0)::BIGINT AS avg_transaction_amount,
                MIN(le.created_at) AS first_transaction_at,
                MAX(le.created_at) AS last_transaction_at
            FROM ledger_entries le
            WHERE le.account_id = $1
              AND le.created_at >= NOW() - ($2 * INTERVAL '1 day')
              AND ($3::SMALLINT IS NULL OR le.direction = $3)
            """,
            account_id,
            period_days,
            direction,
        )
        return dict(row) if row else {}

    async def get_client_timeline(
        self,
        account_id: uuid.UUID,
        period_days: int,
        direction: int | None,
        conn: Connection,
    ) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            """
            SELECT
                DATE_TRUNC('day', le.created_at)::date AS day,
                COALESCE(SUM(CASE WHEN le.direction = 1 THEN le.amount ELSE 0 END), 0) AS credits,
                COALESCE(SUM(CASE WHEN le.direction = -1 THEN le.amount ELSE 0 END), 0) AS debits,
                COALESCE(SUM(CASE WHEN le.direction = 1 THEN le.amount ELSE -le.amount END), 0) AS net,
                COALESCE(COUNT(DISTINCT le.transaction_id), 0) AS transaction_count
            FROM ledger_entries le
            WHERE le.account_id = $1
              AND le.created_at >= NOW() - ($2 * INTERVAL '1 day')
              AND ($3::SMALLINT IS NULL OR le.direction = $3)
            GROUP BY 1
            ORDER BY 1 ASC
            """,
            account_id,
            period_days,
            direction,
        )
        return [dict(r) for r in rows]

    async def get_client_by_category(
        self,
        account_id: uuid.UUID,
        period_days: int,
        direction: int | None,
        conn: Connection,
    ) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            """
            SELECT
                r.id::text AS rule_id,
                r.event_code AS event_code,
                COALESCE(r.description_i18n, '{}'::jsonb) AS description_i18n,
                COALESCE((r.actions ->> 'direction')::SMALLINT, le.direction) AS direction,
                COALESCE(SUM(le.amount), 0) AS amount,
                COALESCE(COUNT(DISTINCT le.transaction_id), 0) AS transaction_count
            FROM ledger_entries le
            JOIN transactions t ON t.id = le.transaction_id
            JOIN rules r ON r.id::text = (t.metadata ->> 'rule_id')
            WHERE le.account_id = $1
              AND le.created_at >= NOW() - ($2 * INTERVAL '1 day')
              AND ($3::SMALLINT IS NULL OR COALESCE((r.actions ->> 'direction')::SMALLINT, le.direction) = $3)
            GROUP BY 1, 2, 3, 4
            ORDER BY amount DESC, rule_id ASC
            """,
            account_id,
            period_days,
            direction,
        )
        return [dict(r) for r in rows]

    async def get_client_streaks(
        self,
        account_id: uuid.UUID,
        period_days: int,
        direction: int | None,
        conn: Connection,
    ) -> dict[str, Any]:
        row = await conn.fetchrow(
            """
            WITH active_days AS (
                SELECT DISTINCT DATE(le.created_at) AS day
                FROM ledger_entries le
                WHERE le.account_id = $1
                  AND le.created_at >= NOW() - ($2 * INTERVAL '1 day')
                                    AND ($3::SMALLINT IS NULL OR le.direction = $3)
            ),
            grouped AS (
                SELECT
                    day,
                    day - (ROW_NUMBER() OVER (ORDER BY day)) * INTERVAL '1 day' AS grp
                FROM active_days
            ),
            islands AS (
                SELECT grp, COUNT(*)::INT AS len, MAX(day) AS end_day
                FROM grouped
                GROUP BY grp
            )
            SELECT
                COALESCE((SELECT len FROM islands ORDER BY end_day DESC LIMIT 1), 0) AS current_streak_days,
                COALESCE((SELECT MAX(len) FROM islands), 0) AS longest_streak_days,
                COALESCE((SELECT COUNT(*)::INT FROM active_days), 0) AS active_days_in_period,
                (SELECT MAX(day) FROM active_days) AS last_active_day
            """,
            account_id,
            period_days,
            direction,
        )
        return dict(row) if row else {}

    async def get_admin_system_summary(
        self,
        start_from: date,
        end_to: date,
        direction: int | None,
        conn: Connection,
    ) -> dict[str, Any]:
        row = await conn.fetchrow(
            """
            WITH account_stats AS (
                SELECT
                    COUNT(*)::INT AS total_users_with_accounts,
                    COALESCE(SUM(balance), 0)::BIGINT AS total_balance_in_system
                FROM accounts
                WHERE owner_type = 'user'
                  AND user_id IS NOT NULL
            ),
            ledger_stats AS (
                SELECT
                    COALESCE(COUNT(DISTINCT le.transaction_id), 0)::INT AS total_transactions,
                    COALESCE(SUM(CASE WHEN le.direction = 1 THEN le.amount ELSE 0 END), 0)::BIGINT AS total_credits_distributed,
                    COALESCE(SUM(CASE WHEN le.direction = -1 THEN le.amount ELSE 0 END), 0)::BIGINT AS total_debits_collected
                FROM ledger_entries le
                JOIN accounts a ON a.id = le.account_id
                WHERE a.owner_type = 'user'
                                    AND le.created_at >= $1::date
                                    AND le.created_at < ($2::date + INTERVAL '1 day')
                                    AND ($3::SMALLINT IS NULL OR le.direction = $3)
            )
            SELECT
                a.total_users_with_accounts,
                a.total_balance_in_system,
                CASE
                    WHEN a.total_users_with_accounts = 0 THEN 0
                    ELSE (a.total_balance_in_system / a.total_users_with_accounts)::BIGINT
                END AS avg_user_balance,
                l.total_transactions,
                l.total_credits_distributed,
                l.total_debits_collected
            FROM account_stats a
            CROSS JOIN ledger_stats l
            """,
            start_from,
            end_to,
            direction,
        )
        return dict(row) if row else {}

    async def get_admin_streaks(
        self,
        start_from: date,
        end_to: date,
        limit: int,
        direction: int | None,
        conn: Connection,
    ) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            """
            WITH daily AS (
                SELECT
                    a.user_id,
                    DATE(le.created_at) AS day
                FROM ledger_entries le
                JOIN accounts a ON a.id = le.account_id
                WHERE a.owner_type = 'user'
                  AND a.user_id IS NOT NULL
                                    AND le.created_at >= $1::date
                                    AND le.created_at < ($2::date + INTERVAL '1 day')
                                    AND ($4::SMALLINT IS NULL OR le.direction = $4)
                GROUP BY a.user_id, DATE(le.created_at)
            ),
            grouped AS (
                SELECT
                    user_id,
                    day,
                    day - (ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY day)) * INTERVAL '1 day' AS grp
                FROM daily
            ),
            islands AS (
                SELECT
                    user_id,
                    grp,
                    COUNT(*)::INT AS len,
                    MAX(day) AS end_day
                FROM grouped
                GROUP BY user_id, grp
            ),
            agg AS (
                SELECT
                    user_id,
                    COALESCE(MAX(len), 0) AS longest_streak_days,
                    COALESCE((ARRAY_AGG(len ORDER BY end_day DESC))[1], 0) AS current_streak_days,
                    COALESCE((ARRAY_AGG(end_day ORDER BY end_day DESC))[1], NULL::date) AS last_active_day,
                    COALESCE(SUM(len), 0)::INT AS active_days_in_period
                FROM islands
                GROUP BY user_id
            )
            SELECT
                user_id,
                current_streak_days,
                longest_streak_days,
                active_days_in_period,
                last_active_day
            FROM agg
            ORDER BY current_streak_days DESC, longest_streak_days DESC, active_days_in_period DESC
            LIMIT $3
            """,
            start_from,
            end_to,
            limit,
            direction,
        )
        return [dict(r) for r in rows]

    async def get_admin_top_by_amount(
        self,
        conn: Connection,
        limit: int = 10,
        offset: int = 0,
        currency: str = "TOKEN",
    ) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            """
            SELECT
                a.user_id,
                COALESCE(SUM(a.balance), 0)::BIGINT AS total_amount
            FROM accounts a
            JOIN competition c ON c.user_id = a.user_id
            WHERE a.owner_type = 'user'
              AND a.currency = $1
              AND a.user_id IS NOT NULL
            GROUP BY a.user_id
            ORDER BY total_amount DESC, a.user_id ASC
            LIMIT $2 OFFSET $3
            """,
            currency,
            limit,
            offset,
        )
        return [dict(r) for r in rows]

    async def get_admin_top_by_amount_count(
        self,
        conn: Connection,
        currency: str = "TOKEN",
    ) -> int:
        count = await conn.fetchval(
            """
            SELECT COUNT(*)::INT
            FROM (
                SELECT a.user_id
                FROM accounts a
                JOIN competition c ON c.user_id = a.user_id
                WHERE a.owner_type = 'user'
                  AND a.currency = $1
                  AND a.user_id IS NOT NULL
                GROUP BY a.user_id
            ) ranked_users
            """,
            currency,
        )
        return int(count or 0)

    async def get_admin_top_by_amount_rank(
        self,
        conn: Connection,
        user_id: uuid.UUID,
        currency: str = "TOKEN",
    ) -> int | None:
        rank = await conn.fetchval(
            """
            WITH ranked AS (
                SELECT
                    a.user_id,
                    RANK() OVER (
                        ORDER BY COALESCE(SUM(a.balance), 0)::BIGINT DESC, a.user_id ASC
                    )::INT AS rank_position
                FROM accounts a
                JOIN competition c ON c.user_id = a.user_id
                WHERE a.owner_type = 'user'
                  AND a.currency = $1
                  AND a.user_id IS NOT NULL
                GROUP BY a.user_id
            )
            SELECT rank_position
            FROM ranked
            WHERE user_id = $2
            """,
            currency,
            user_id,
        )
        return int(rank) if rank is not None else None
