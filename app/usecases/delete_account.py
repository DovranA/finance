from __future__ import annotations

import uuid

from asyncpg import Pool

from app.infrastructure.db.transaction import transaction
from app.infrastructure.redis.cache import CacheService


class DeleteAccountUseCase:
    """Delete or deactivate all accounts that belong to a user."""

    def __init__(
        self,
        pool: Pool,
        cache: CacheService | None = None,
    ) -> None:
        self._pool = pool
        self._cache = cache

    async def execute(self, user_id: uuid.UUID, hard_delete: bool = False) -> dict:
        async with transaction(self._pool) as conn:
            account_rows = await conn.fetch(
                "SELECT id FROM accounts WHERE user_id = $1",
                user_id,
            )
            account_ids = [row["id"] for row in account_rows]

            if not account_ids:
                return {
                    "user_id": str(user_id),
                    "deleted": False,
                    "hard_delete": hard_delete,
                    "accounts_affected": 0,
                }

            if hard_delete:
                await conn.execute(
                    "DELETE FROM ledger_entries WHERE account_id = ANY($1::uuid[])",
                    account_ids,
                )
                await conn.execute(
                    "DELETE FROM accounts WHERE user_id = $1",
                    user_id,
                )
                affected_count = len(account_ids)
            else:
                affected_count = await conn.fetchval(
                    "WITH updated AS ("
                    "  UPDATE accounts "
                    "  SET is_active = FALSE, updated_at = NOW() "
                    "  WHERE user_id = $1 AND is_active = TRUE "
                    "  RETURNING id"
                    ") "
                    "SELECT COUNT(*) FROM updated",
                    user_id,
                )

        if self._cache:
            for account_id in account_ids:
                await self._cache.invalidate_balance(account_id)

        return {
            "user_id": str(user_id),
            "deleted": bool(affected_count),
            "hard_delete": hard_delete,
            "accounts_affected": int(affected_count),
        }
