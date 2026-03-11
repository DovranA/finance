"""Dishka dependency injection container — wires infrastructure to use cases."""

from __future__ import annotations

from typing import AsyncIterable

import redis.asyncio as redis
from asyncpg import Pool
from dishka import Provider, Scope, provide, make_async_container, AsyncContainer

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.repositories.account_repo import AccountRepository
from app.domain.repositories.transfer_repo import TransactionRepository
from app.domain.repositories.ledger_repo import LedgerRepository
from app.domain.repositories.rule_repo import RuleRepository
from app.domain.policies.engine import ConditionEngine
from app.domain.policies.registry import ValidatorRegistry, registry as global_registry
from app.domain.policies.validators.min_balance import MinBalanceValidator
from app.domain.policies.validators.role_required import RoleRequiredValidator
from app.domain.policies.validators.daily_limit import DailyLimitValidator
from app.domain.policies.validators.one_time_only import OneTimeValidator
from app.domain.policies.validators.required_metadata import RequiredMetadataValidator
from app.infrastructure.db.connection import create_pool, close_pool
from app.infrastructure.db.repositories.account_repo_impl import PgAccountRepository
from app.infrastructure.db.repositories.transaction_repo_impl import (
    PgTransactionRepository,
)
from app.infrastructure.db.repositories.ledger_repo_impl import PgLedgerRepository
from app.infrastructure.db.repositories.rule_repo_impl import PgRuleRepository
from app.infrastructure.redis.cache import CacheService
from app.infrastructure.redis.client import create_redis_pool, close_redis
from app.usecases.get_balance import GetBalanceUseCase
from app.usecases.set_balance import SetBalanceUseCase
from app.usecases.transfer import TransferUseCase
from app.usecases.rule_crud import (
    CreateRuleUseCase,
    GetRuleUseCase,
    ListRulesUseCase,
    UpdateRuleUseCase,
    DeleteRuleUseCase,
)
from app.usecases.apply_rule import ApplyRuleUseCase


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
    transaction_repo = provide(
        PgTransactionRepository,
        provides=TransactionRepository,
    )
    ledger_repo = provide(
        PgLedgerRepository,
        provides=LedgerRepository,
    )
    rule_repo = provide(
        PgRuleRepository,
        provides=RuleRepository,
    )


class PolicyProvider(Provider):
    """Provides the condition engine with all registered validators — APP-scoped."""

    scope = Scope.APP

    @provide
    def get_registry(self, cache: CacheService | None) -> ValidatorRegistry:
        global_registry.register(MinBalanceValidator())
        global_registry.register(RoleRequiredValidator())
        global_registry.register(DailyLimitValidator())
        global_registry.register(OneTimeValidator(cache=cache))
        global_registry.register(RequiredMetadataValidator())
        return global_registry

    @provide
    def get_condition_engine(self, registry: ValidatorRegistry) -> ConditionEngine:
        return ConditionEngine(registry)


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
    def set_balance_uc(
        self,
        pool: Pool,
        account_repo: AccountRepository,
        transaction_repo: TransactionRepository,
        ledger_repo: LedgerRepository,
        cache: CacheService | None,
    ) -> SetBalanceUseCase:
        return SetBalanceUseCase(
            pool=pool,
            account_repo=account_repo,
            transaction_repo=transaction_repo,
            ledger_repo=ledger_repo,
            cache=cache,
        )

    @provide
    def transfer_uc(
        self,
        pool: Pool,
        account_repo: AccountRepository,
        transaction_repo: TransactionRepository,
        ledger_repo: LedgerRepository,
        cache: CacheService | None,
    ) -> TransferUseCase:
        return TransferUseCase(
            pool=pool,
            account_repo=account_repo,
            transaction_repo=transaction_repo,
            ledger_repo=ledger_repo,
            cache=cache,
        )

    # ── Rule use cases ───────────────────────────────────

    @provide
    def create_rule_uc(
        self, pool: Pool, rule_repo: RuleRepository, cache: CacheService | None
    ) -> CreateRuleUseCase:
        return CreateRuleUseCase(pool=pool, rule_repo=rule_repo, cache=cache)

    @provide
    def get_rule_uc(self, pool: Pool, rule_repo: RuleRepository) -> GetRuleUseCase:
        return GetRuleUseCase(pool=pool, rule_repo=rule_repo)

    @provide
    def list_rules_uc(self, pool: Pool, rule_repo: RuleRepository) -> ListRulesUseCase:
        return ListRulesUseCase(pool=pool, rule_repo=rule_repo)

    @provide
    def update_rule_uc(
        self, pool: Pool, rule_repo: RuleRepository, cache: CacheService | None
    ) -> UpdateRuleUseCase:
        return UpdateRuleUseCase(pool=pool, rule_repo=rule_repo, cache=cache)

    @provide
    def delete_rule_uc(
        self, pool: Pool, rule_repo: RuleRepository, cache: CacheService | None
    ) -> DeleteRuleUseCase:
        return DeleteRuleUseCase(pool=pool, rule_repo=rule_repo, cache=cache)

    @provide
    def apply_rule_uc(
        self,
        pool: Pool,
        rule_repo: RuleRepository,
        account_repo: AccountRepository,
        transaction_repo: TransactionRepository,
        ledger_repo: LedgerRepository,
        condition_engine: ConditionEngine,
        cache: CacheService | None,
    ) -> ApplyRuleUseCase:
        return ApplyRuleUseCase(
            pool=pool,
            rule_repo=rule_repo,
            account_repo=account_repo,
            transaction_repo=transaction_repo,
            ledger_repo=ledger_repo,
            condition_engine=condition_engine,
            cache=cache,
        )


def create_container() -> AsyncContainer:
    """Build the Dishka async container with all providers."""
    return make_async_container(
        ConfigProvider(),
        InfrastructureProvider(),
        RepositoryProvider(),
        PolicyProvider(),
        UseCaseProvider(),
    )
