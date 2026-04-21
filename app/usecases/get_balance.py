"""Get Balance Use Case — with optional Redis cache."""

from __future__ import annotations

import uuid

from asyncpg import Pool

from app.core.logging import get_logger
from app.domain.repositories.account_repo import AccountRepository
from app.domain.value_objects.enums import Currency
from app.infrastructure.redis.cache import CacheService

logger = get_logger(__name__)


class GetBalanceUseCase:
    """Retrieve account balance for a user, using Redis cache when available."""

    def __init__(
        self,
        pool: Pool,
        account_repo: AccountRepository,
        cache: CacheService | None = None,
    ) -> None:
        self._pool = pool
        self._account_repo = account_repo
        self._cache = cache

    async def execute(self, user_id: uuid.UUID, currency: str | None = None) -> dict:
        requested_currency = currency.upper() if currency else None

        # Read-only — no transaction needed, just acquire a connection
        async with self._pool.acquire() as conn:
            accounts = await self._account_repo.list_by_owner_id(user_id, conn)

        if not accounts:
            return {
                "user_id": str(user_id),
                "found": False,
                "balances": [],
            }

        balances: list[dict] = []
        selected = None

        for account in accounts:
            if not account.is_active:
                continue
            cached_flag = False
            value = account.balance

            if self._cache:
                cached_val = await self._cache.get_cached_balance(account.id)
                if cached_val is not None:
                    value = cached_val
                    cached_flag = True
                else:
                    await self._cache.set_cached_balance(account.id, account.balance)

            item = {
                "account_id": str(account.id),
                "currency": account.currency,
                "balance": value,
                "cached": cached_flag,
            }
            balances.append(item)

            if requested_currency and account.currency.upper() == requested_currency:
                selected = item

        if requested_currency and selected is None:
            return {
                "user_id": str(user_id),
                "found": False,
                "cached": False,
                "balances": balances,
            }

        if selected is None:
            selected = balances[0]

        return {
            "user_id": str(user_id),
            "found": True,
            "cached": selected["cached"],
            "balances": balances,
        }
