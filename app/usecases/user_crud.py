"""Use case for creating a default finance account for newly registered users."""

from __future__ import annotations

import uuid

from asyncpg import Pool

from app.core.logging import get_logger
from app.domain.entities.account import Account
from app.domain.repositories.account_repo import AccountRepository
from app.infrastructure.db.transaction import transaction

logger = get_logger(__name__)


class RegisterUserUseCase:
    """Create a default TOKEN account for a newly registered user if it does not exist."""

    def __init__(
        self,
        pool: Pool,
        account_repo: AccountRepository,
    ) -> None:
        self._pool = pool
        self._account_repo = account_repo

    async def execute(
        self,
        *,
        user_id: uuid.UUID,
        role: str | None,
        currency: str = "TOKEN",
    ) -> dict:
        currency = currency.upper()
        owner_type = "user"

        async with transaction(self._pool) as conn:
            existing_accounts = await self._account_repo.list_by_owner_id(user_id, conn)
            existing_account = next(
                (
                    account
                    for account in existing_accounts
                    if account.currency.upper() == currency and account.is_active
                ),
                None,
            )
            if existing_account is not None:
                logger.info(
                    "registered_user_account_already_exists",
                    user_id=str(user_id),
                    account_id=str(existing_account.id),
                    currency=currency,
                )
                return {
                    "created": False,
                    "account_id": str(existing_account.id),
                    "user_id": str(user_id),
                    "currency": existing_account.currency,
                }

            account = Account.create(
                user_id=user_id,
                currency=currency,
                owner_type=owner_type,
                balance=0,
            )
            await self._account_repo.create(account, conn)

        logger.info(
            "registered_user_account_created",
            user_id=str(user_id),
            account_id=str(account.id),
            currency=currency,
            owner_type=owner_type,
        )
        return {
            "created": True,
            "account_id": str(account.id),
            "user_id": str(user_id),
            "currency": currency,
        }


class UserDeleteUseCase:
    def __init__(
        self,
        pool: Pool,
        account_repo: AccountRepository,
    ) -> None:
        self._pool = pool
        self._account_repo = account_repo

    async def execute(
        self,
        user_id: uuid.UUID,
        role: str | None,
    ) -> dict:
        async with transaction(self._pool) as conn:
            account_ids = [
                account.id
                for account in await self._account_repo.list_by_owner_id(user_id, conn)
                if account.is_active
            ]

            if not account_ids:
                return {
                    "user_id": str(user_id),
                    "deleted": False,
                    "hard_delete": False,
                    "accounts_affected": 0,
                }

            await conn.execute(
                "UPDATE accounts SET is_active = FALSE, updated_at = NOW() WHERE user_id = $1",
                user_id,
            )

        return {
            "user_id": str(user_id),
            "deleted": True,
            "hard_delete": False,
            "accounts_affected": len(account_ids),
        }


class UpdateIsActiveUserUseCase:
    def __init__(
        self,
        pool: Pool,
        account_repo: AccountRepository,
    ) -> None:
        self._pool = pool
        self._account_repo = account_repo

    async def execute(self, user_id: uuid.UUID, is_blocked: bool):
        async with transaction(self._pool) as conn:
            account_ids = [
                account.id
                for account in await self._account_repo.list_by_owner_id(user_id, conn)
            ]

            if not account_ids:
                return {
                    "user_id": str(user_id),
                    "is_active": True,
                    "accounts_affected": 0,
                }

            await self._account_repo.update_is_active(
                user_id=user_id, is_active=(not is_blocked), conn=conn
            )
        return {
            "user_id": str(user_id),
            "is_active": (not is_blocked),
            "accounts_affected": len(account_ids),
        }
