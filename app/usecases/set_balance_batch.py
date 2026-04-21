from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from asyncpg import Pool

from app.domain.repositories.account_repo import AccountRepository
from app.usecases.set_balance import SetBalanceUseCase


class BatchSetBalanceUseCase:
    """Apply set-balance requests for multiple users."""

    def __init__(
        self,
        pool: Pool,
        set_balance_uc: SetBalanceUseCase,
        account_repo: AccountRepository,
        max_parallelism: int = 20,
    ) -> None:
        self._pool = pool
        self._set_balance_uc = set_balance_uc
        self._account_repo = account_repo
        self._max_parallelism = max(1, max_parallelism)

    async def _process_item(
        self,
        *,
        item: dict[str, Any],
        existing_user_ids: set[UUID],
    ) -> dict[str, Any]:
        user_id = item["user_id"]
        new_balance = item["new_balance"]
        currency = str(item["currency"]).upper()
        account_existed = user_id in existing_user_ids

        try:
            result = await self._set_balance_uc.execute(
                user_id=user_id,
                new_balance=new_balance,
                currency=currency,
            )
            return {
                "user_id": str(user_id),
                "new_balance": new_balance,
                "currency": currency,
                "account_existed": account_existed,
                "success": True,
                "error": None,
                "balances": result.get("balances") or [],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "user_id": str(user_id),
                "new_balance": new_balance,
                "currency": currency,
                "account_existed": account_existed,
                "success": False,
                "error": str(exc),
                "balances": [],
            }

    async def execute(self, *, items: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(items)
        if total == 0:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "results": [],
            }

        results: list[dict[str, Any]] = []

        requested_user_ids: list[UUID] = [item["user_id"] for item in items]
        deduped_user_ids = list(dict.fromkeys(requested_user_ids))
        async with self._pool.acquire() as conn:
            existing_accounts = await self._account_repo.list_by_owner_ids(
                deduped_user_ids,
                conn,
            )
        existing_user_ids = {
            account.user_id for account in existing_accounts if account.is_active
        }

        for i in range(0, total, self._max_parallelism):
            chunk = items[i : i + self._max_parallelism]
            chunk_results = await asyncio.gather(
                *[
                    self._process_item(item=item, existing_user_ids=existing_user_ids)
                    for item in chunk
                ]
            )
            results.extend(chunk_results)

        success_count = sum(1 for item in results if item["success"])
        failed_count = total - success_count

        return {
            "total": total,
            "success": success_count,
            "failed": failed_count,
            "results": results,
        }
