"""Admin actions use cases — manage economic actions and versions."""

from __future__ import annotations

import uuid

from asyncpg import Pool

from app.core.logging import get_logger
from app.domain.entities.economic_action import EconomicAction, EconomicActionVersion
from app.domain.repositories.economic_action_repo import EconomicActionRepository
from app.infrastructure.db.transaction import transaction
from app.infrastructure.redis.cache import CacheService

logger = get_logger(__name__)


class CreateEconomicActionUseCase:
    """Create a new dynamic action type (e.g. LIKE, SHARE, VIEW)."""

    def __init__(
        self,
        pool: Pool,
        repo: EconomicActionRepository,
    ) -> None:
        self._pool = pool
        self._repo = repo

    async def execute(self, code: str, description: str = "") -> EconomicAction:
        action = EconomicAction.create(code=code, description=description)
        async with transaction(self._pool) as conn:
            await self._repo.create_action(action, conn)
        logger.info("economic_action_created", code=action.code, id=str(action.id))
        return action


class CreateEconomicVersionUseCase:
    """Create a new reward version for an existing action."""

    def __init__(
        self,
        pool: Pool,
        repo: EconomicActionRepository,
    ) -> None:
        self._pool = pool
        self._repo = repo

    async def execute(
        self,
        action_id: uuid.UUID,
        publisher_reward: int,
        actor_reward: int,
        platform_fee: int,
        treasury_cut: int,
    ) -> EconomicActionVersion:
        async with transaction(self._pool) as conn:
            action = await self._repo.get_action_by_id(action_id, conn)
            if action is None:
                raise ValueError(f"Economic action {action_id} not found")

            next_version = await self._repo.get_next_version_number(action_id, conn)

            version = EconomicActionVersion.create(
                action_id=action_id,
                publisher_reward=publisher_reward,
                actor_reward=actor_reward,
                platform_fee=platform_fee,
                treasury_cut=treasury_cut,
                version=next_version,
            )
            await self._repo.create_version(version, conn)

        logger.info(
            "economic_version_created",
            action_id=str(action_id),
            version=next_version,
        )
        return version


class ActivateEconomicVersionUseCase:
    """Activate a specific version for an action (deactivates all others)."""

    def __init__(
        self,
        pool: Pool,
        repo: EconomicActionRepository,
        cache: CacheService | None = None,
    ) -> None:
        self._pool = pool
        self._repo = repo
        self._cache = cache

    async def execute(self, action_id: uuid.UUID, version_id: uuid.UUID) -> None:
        async with transaction(self._pool) as conn:
            action = await self._repo.get_action_by_id(action_id, conn)
            if action is None:
                raise ValueError(f"Economic action {action_id} not found")

            await self._repo.activate_version(version_id, action_id, conn)

        # Invalidate cache so next lookup fetches the new version
        if self._cache:
            await self._cache.invalidate_economic_config(action.code)

        logger.info(
            "economic_version_activated",
            action_id=str(action_id),
            version_id=str(version_id),
        )


class DisableEconomicActionUseCase:
    """Disable an economic action (no new rewards will be given)."""

    def __init__(
        self,
        pool: Pool,
        repo: EconomicActionRepository,
        cache: CacheService | None = None,
    ) -> None:
        self._pool = pool
        self._repo = repo
        self._cache = cache

    async def execute(self, action_id: uuid.UUID) -> None:
        async with transaction(self._pool) as conn:
            action = await self._repo.get_action_by_id(action_id, conn)
            if action is None:
                raise ValueError(f"Economic action {action_id} not found")

            await self._repo.set_active(action_id, False, conn)

        if self._cache:
            await self._cache.invalidate_economic_config(action.code)

        logger.info("economic_action_disabled", action_id=str(action_id))


class ListEconomicActionsUseCase:
    """List all economic actions with their versions."""

    def __init__(
        self,
        pool: Pool,
        repo: EconomicActionRepository,
    ) -> None:
        self._pool = pool
        self._repo = repo

    async def execute(self) -> list[dict]:
        async with transaction(self._pool) as conn:
            actions = await self._repo.list_actions(conn)
            result = []
            for action in actions:
                versions = await self._repo.list_versions(action.id, conn)
                result.append({
                    "id": str(action.id),
                    "code": action.code,
                    "description": action.description,
                    "is_active": action.is_active,
                    "created_at": action.created_at.isoformat(),
                    "versions": [
                        {
                            "id": str(v.id),
                            "version": v.version,
                            "publisher_reward": v.publisher_reward,
                            "actor_reward": v.actor_reward,
                            "platform_fee": v.platform_fee,
                            "treasury_cut": v.treasury_cut,
                            "is_active": v.is_active,
                            "active_from": v.active_from.isoformat(),
                        }
                        for v in versions
                    ],
                })
            return result
