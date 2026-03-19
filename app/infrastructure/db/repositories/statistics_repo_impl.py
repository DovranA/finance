"""Concrete statistics repository with aggregate SQL queries."""

from __future__ import annotations

import uuid
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
                COALESCE(t.reference_type, 'unknown') AS category,
                COALESCE(t.reference_type, 'unknown') AS event_code,
                COALESCE(r.description_i18n, '{}'::jsonb) AS description_i18n,
                r.description AS description,
                COALESCE(SUM(CASE WHEN le.direction = 1 THEN le.amount ELSE 0 END), 0) AS credits,
                COALESCE(SUM(CASE WHEN le.direction = -1 THEN le.amount ELSE 0 END), 0) AS debits,
                COALESCE(SUM(CASE WHEN le.direction = 1 THEN le.amount ELSE -le.amount END), 0) AS net,
                COALESCE(COUNT(DISTINCT le.transaction_id), 0) AS transaction_count
            FROM ledger_entries le
            JOIN transactions t ON t.id = le.transaction_id
            LEFT JOIN rules r ON r.event_code = t.reference_type
            WHERE le.account_id = $1
              AND le.created_at >= NOW() - ($2 * INTERVAL '1 day')
              AND ($3::SMALLINT IS NULL OR le.direction = $3)
            GROUP BY 1, 2, 3, 4
            ORDER BY transaction_count DESC, category ASC
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
        period_days: int,
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
                  AND le.created_at >= NOW() - ($1 * INTERVAL '1 day')
                                    AND ($2::SMALLINT IS NULL OR le.direction = $2)
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
            period_days,
            direction,
        )
        return dict(row) if row else {}

    async def get_admin_streaks(
        self,
        period_days: int,
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
                  AND le.created_at >= NOW() - ($1 * INTERVAL '1 day')
                                    AND ($3::SMALLINT IS NULL OR le.direction = $3)
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
            LIMIT $2
            """,
            period_days,
            limit,
            direction,
        )
        return [dict(r) for r in rows]
