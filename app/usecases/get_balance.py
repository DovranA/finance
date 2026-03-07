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

    async def execute(self, user_id: uuid.UUID) -> dict:
        # Read-only — no transaction needed, just acquire a connection
        async with self._pool.acquire() as conn:
            account = await self._account_repo.get_by_owner_id(user_id, conn)

        if account is None:
            return {
                "user_id": str(user_id),
                "balance": 0,
                "currency": Currency.TMT,
                "found": False,
            }

        # Check cache
        if self._cache:
            cached = await self._cache.get_cached_balance(account.id)
            if cached is not None:
                logger.debug("balance_cache_hit", user_id=str(user_id))
                return {
                    "user_id": str(user_id),
                    "account_id": str(account.id),
                    "balance": cached,
                    "currency": account.currency,
                    "found": True,
                    "cached": True,
                }

        # Set cache
        if self._cache:
            await self._cache.set_cached_balance(account.id, account.balance)

        return {
            "user_id": str(user_id),
            "account_id": str(account.id),
            "balance": account.balance,
            "currency": account.currency,
            "found": True,
            "cached": False,
        }
