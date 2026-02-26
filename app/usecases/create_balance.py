"""Get Balance Use Case — with optional Redis cache."""

from __future__ import annotations

import uuid

from asyncpg import Pool

from app.core.logging import get_logger
from app.domain.entities.account import Account
from app.domain.repositories.account_repo import AccountRepository
from app.domain.value_objects.enums import Currency
from app.infrastructure.db.transaction import transaction
from app.infrastructure.redis.cache import CacheService

logger = get_logger(__name__)


class CreateBalanceUseCase:
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
        async with transaction(self._pool) as conn:
            account = await self._account_repo.get_by_user_id(user_id, conn)

            if account is None:
                account = Account.create(user_id=user_id, currency=Currency.TMT)
                await self._account_repo.create(account, conn)

        # 🔹 здесь conn уже НЕ нужен — можно кешировать
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
