"""Dishka dependency injection container — wires infrastructure to use cases."""

from __future__ import annotations

from typing import AsyncIterable

import redis.asyncio as redis
from asyncpg import Pool
from dishka import Provider, Scope, provide, make_async_container, AsyncContainer

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.repositories.account_repo import AccountRepository
from app.domain.repositories.actor_action_repo import ActorActionRepository
from app.domain.repositories.economic_action_repo import EconomicActionRepository
from app.domain.repositories.idempotency_repo import IdempotencyRepository
from app.domain.repositories.ledger_repo import LedgerRepository
from app.domain.repositories.outbox_repo import OutboxRepository
from app.domain.repositories.processed_event_repo import ProcessedEventRepository
from app.domain.repositories.reward_batch_repo import RewardBatchRepository
from app.infrastructure.db.connection import create_pool, close_pool
from app.infrastructure.db.repositories.account_repo_impl import PgAccountRepository
from app.infrastructure.db.repositories.actor_action_repo_impl import (
    PgActorActionRepository,
)
from app.infrastructure.db.repositories.economic_action_repo_impl import (
    PgEconomicActionRepository,
)
from app.infrastructure.db.repositories.idempotency_repo_impl import (
    PgIdempotencyRepository,
)
from app.infrastructure.db.repositories.ledger_repo_impl import PgLedgerRepository
from app.infrastructure.db.repositories.outbox_repo_impl import PgOutboxRepository
from app.infrastructure.db.repositories.processed_event_repo_impl import (
    PgProcessedEventRepository,
)
from app.infrastructure.db.repositories.reward_batch_repo_impl import (
    PgRewardBatchRepository,
)
from app.infrastructure.db.repositories.treasury_repo_impl import PgTreasuryRepository
from app.infrastructure.redis.cache import CacheService
from app.infrastructure.redis.client import create_redis_pool, close_redis
from app.usecases.admin_actions import (
    ActivateEconomicVersionUseCase,
    CreateEconomicActionUseCase,
    CreateEconomicVersionUseCase,
    DisableEconomicActionUseCase,
    ListEconomicActionsUseCase,
)
from app.usecases.get_balance import GetBalanceUseCase
from app.usecases.create_balance import CreateBalanceUseCase
from app.usecases.process_reward_batch import ProcessRewardBatchUseCase
from app.usecases.process_reward_event import ProcessRewardEventUseCase

logger = get_logger(__name__)


class ConfigProvider(Provider):
    """Provides application settings."""

    scope = Scope.APP

    @provide
    def get_settings(self) -> Settings:
        return get_settings()


class InfrastructureProvider(Provider):
    """Provides DB pool, Redis client, and cache — APP-scoped singletons."""

    scope = Scope.APP

    @provide
    async def get_pool(self, settings: Settings) -> AsyncIterable[Pool]:
        pool = await create_pool(settings.postgres)
        yield pool
        await close_pool(pool)

    @provide
    async def get_redis(self, settings: Settings) -> AsyncIterable[redis.Redis | None]:
        try:
            client = await create_redis_pool(settings.redis)
        except Exception:
            logger.warning("redis_unavailable_continuing_without_cache")
            yield None
            return

        yield client
        await close_redis(client)

    @provide
    def get_cache(self, client: redis.Redis | None) -> CacheService | None:
        return CacheService(client) if client else None


class RepositoryProvider(Provider):
    """Provides repository implementations — APP-scoped singletons (stateless)."""

    scope = Scope.APP

    account_repo = provide(
        PgAccountRepository,
        provides=AccountRepository,
    )
    idempotency_repo = provide(
        PgIdempotencyRepository,
        provides=IdempotencyRepository,
    )
    ledger_repo = provide(
        PgLedgerRepository,
        provides=LedgerRepository,
    )
    economic_action_repo = provide(
        PgEconomicActionRepository,
        provides=EconomicActionRepository,
    )
    actor_action_repo = provide(
        PgActorActionRepository,
        provides=ActorActionRepository,
    )
    reward_batch_repo = provide(
        PgRewardBatchRepository,
        provides=RewardBatchRepository,
    )
    processed_event_repo = provide(
        PgProcessedEventRepository,
        provides=ProcessedEventRepository,
    )
    outbox_repo = provide(
        PgOutboxRepository,
        provides=OutboxRepository,
    )
    treasury_repo = provide(
        PgTreasuryRepository,
        provides=PgTreasuryRepository,
    )


class UseCaseProvider(Provider):
    """Provides use cases — REQUEST-scoped (created per HTTP request)."""

    scope = Scope.REQUEST

    @provide
    def get_balance_uc(
        self,
        pool: Pool,
        account_repo: AccountRepository,
        cache: CacheService | None,
    ) -> GetBalanceUseCase:
        return GetBalanceUseCase(
            pool=pool,
            account_repo=account_repo,
            cache=cache,
        )

    @provide
    def create_balance_uc(
        self,
        pool: Pool,
        account_repo: AccountRepository,
        cache: CacheService | None,
    ) -> CreateBalanceUseCase:
        return CreateBalanceUseCase(
            pool=pool,
            account_repo=account_repo,
            cache=cache,
        )

    @provide
    def create_action_uc(
        self,
        pool: Pool,
        repo: EconomicActionRepository,
    ) -> CreateEconomicActionUseCase:
        return CreateEconomicActionUseCase(pool=pool, repo=repo)

    @provide
    def create_version_uc(
        self,
        pool: Pool,
        repo: EconomicActionRepository,
    ) -> CreateEconomicVersionUseCase:
        return CreateEconomicVersionUseCase(pool=pool, repo=repo)

    @provide
    def activate_version_uc(
        self,
        pool: Pool,
        repo: EconomicActionRepository,
        cache: CacheService | None,
    ) -> ActivateEconomicVersionUseCase:
        return ActivateEconomicVersionUseCase(pool=pool, repo=repo, cache=cache)

    @provide
    def disable_action_uc(
        self,
        pool: Pool,
        repo: EconomicActionRepository,
        cache: CacheService | None,
    ) -> DisableEconomicActionUseCase:
        return DisableEconomicActionUseCase(pool=pool, repo=repo, cache=cache)

    @provide
    def list_actions_uc(
        self,
        pool: Pool,
        repo: EconomicActionRepository,
    ) -> ListEconomicActionsUseCase:
        return ListEconomicActionsUseCase(pool=pool, repo=repo)

    @provide
    def process_reward_event_uc(
        self,
        pool: Pool,
        account_repo: AccountRepository,
        ledger_repo: LedgerRepository,
        actor_action_repo: ActorActionRepository,
        economic_action_repo: EconomicActionRepository,
        reward_batch_repo: RewardBatchRepository,
        processed_event_repo: ProcessedEventRepository,
        outbox_repo: OutboxRepository,
        cache: CacheService | None,
    ) -> ProcessRewardEventUseCase:
        return ProcessRewardEventUseCase(
            pool=pool,
            account_repo=account_repo,
            ledger_repo=ledger_repo,
            actor_action_repo=actor_action_repo,
            economic_action_repo=economic_action_repo,
            reward_batch_repo=reward_batch_repo,
            processed_event_repo=processed_event_repo,
            outbox_repo=outbox_repo,
            cache=cache,
        )

    @provide
    def process_reward_batch_uc(
        self,
        pool: Pool,
        account_repo: AccountRepository,
        ledger_repo: LedgerRepository,
        reward_batch_repo: RewardBatchRepository,
        treasury_repo: PgTreasuryRepository,
        outbox_repo: OutboxRepository,
        cache: CacheService | None,
    ) -> ProcessRewardBatchUseCase:
        return ProcessRewardBatchUseCase(
            pool=pool,
            account_repo=account_repo,
            ledger_repo=ledger_repo,
            reward_batch_repo=reward_batch_repo,
            treasury_repo=treasury_repo,
            outbox_repo=outbox_repo,
            cache=cache,
        )


def create_container() -> AsyncContainer:
    """Build the Dishka async container with all providers."""
    return make_async_container(
        ConfigProvider(),
        InfrastructureProvider(),
        RepositoryProvider(),
        UseCaseProvider(),
    )
