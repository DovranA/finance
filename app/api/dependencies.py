"""FastAPI dependency injection — wires infrastructure to use cases."""

from __future__ import annotations

from functools import lru_cache
from typing import AsyncGenerator

from asyncpg import Pool
from fastapi import Request

from app.infrastructure.db.repositories.account_repo_impl import PgAccountRepository
from app.infrastructure.db.repositories.actor_action_repo_impl import PgActorActionRepository
from app.infrastructure.db.repositories.economic_action_repo_impl import PgEconomicActionRepository
from app.infrastructure.db.repositories.ledger_repo_impl import PgLedgerRepository
from app.infrastructure.db.repositories.processed_event_repo_impl import PgProcessedEventRepository
from app.infrastructure.db.repositories.reward_batch_repo_impl import PgRewardBatchRepository
from app.infrastructure.db.repositories.treasury_repo_impl import PgTreasuryRepository
from app.infrastructure.db.repositories.outbox_repo_impl import PgOutboxRepository
from app.infrastructure.redis.cache import CacheService
from app.usecases.admin_actions import (
    ActivateEconomicVersionUseCase,
    CreateEconomicActionUseCase,
    CreateEconomicVersionUseCase,
    DisableEconomicActionUseCase,
    ListEconomicActionsUseCase,
)
from app.usecases.get_balance import GetBalanceUseCase
from app.usecases.process_reward_batch import ProcessRewardBatchUseCase
from app.usecases.process_reward_event import ProcessRewardEventUseCase


# ── Singleton repositories ───────────────────────────────────

@lru_cache(maxsize=1)
def get_account_repo() -> PgAccountRepository:
    return PgAccountRepository()


@lru_cache(maxsize=1)
def get_ledger_repo() -> PgLedgerRepository:
    return PgLedgerRepository()


@lru_cache(maxsize=1)
def get_economic_action_repo() -> PgEconomicActionRepository:
    return PgEconomicActionRepository()


@lru_cache(maxsize=1)
def get_actor_action_repo() -> PgActorActionRepository:
    return PgActorActionRepository()


@lru_cache(maxsize=1)
def get_reward_batch_repo() -> PgRewardBatchRepository:
    return PgRewardBatchRepository()


@lru_cache(maxsize=1)
def get_processed_event_repo() -> PgProcessedEventRepository:
    return PgProcessedEventRepository()


@lru_cache(maxsize=1)
def get_treasury_repo() -> PgTreasuryRepository:
    return PgTreasuryRepository()


@lru_cache(maxsize=1)
def get_outbox_repo() -> PgOutboxRepository:
    return PgOutboxRepository()


# ── Use case factories ──────────────────────────────────────

def get_pool(request: Request) -> Pool:
    return request.app.state.db_pool


def get_cache(request: Request) -> CacheService | None:
    redis_client = getattr(request.app.state, "redis_client", None)
    return CacheService(redis_client) if redis_client else None


def get_create_action_uc(request: Request) -> CreateEconomicActionUseCase:
    return CreateEconomicActionUseCase(
        pool=get_pool(request),
        repo=get_economic_action_repo(),
    )


def get_create_version_uc(request: Request) -> CreateEconomicVersionUseCase:
    return CreateEconomicVersionUseCase(
        pool=get_pool(request),
        repo=get_economic_action_repo(),
    )


def get_activate_version_uc(request: Request) -> ActivateEconomicVersionUseCase:
    return ActivateEconomicVersionUseCase(
        pool=get_pool(request),
        repo=get_economic_action_repo(),
        cache=get_cache(request),
    )


def get_disable_action_uc(request: Request) -> DisableEconomicActionUseCase:
    return DisableEconomicActionUseCase(
        pool=get_pool(request),
        repo=get_economic_action_repo(),
        cache=get_cache(request),
    )


def get_list_actions_uc(request: Request) -> ListEconomicActionsUseCase:
    return ListEconomicActionsUseCase(
        pool=get_pool(request),
        repo=get_economic_action_repo(),
    )


def get_balance_uc(request: Request) -> GetBalanceUseCase:
    return GetBalanceUseCase(
        pool=get_pool(request),
        account_repo=get_account_repo(),
        cache=get_cache(request),
    )


def get_process_reward_event_uc(request: Request) -> ProcessRewardEventUseCase:
    return ProcessRewardEventUseCase(
        pool=get_pool(request),
        account_repo=get_account_repo(),
        ledger_repo=get_ledger_repo(),
        actor_action_repo=get_actor_action_repo(),
        economic_action_repo=get_economic_action_repo(),
        reward_batch_repo=get_reward_batch_repo(),
        processed_event_repo=get_processed_event_repo(),
        outbox_repo=get_outbox_repo(),
        cache=get_cache(request),
    )


def get_process_reward_batch_uc(request: Request) -> ProcessRewardBatchUseCase:
    return ProcessRewardBatchUseCase(
        pool=get_pool(request),
        account_repo=get_account_repo(),
        ledger_repo=get_ledger_repo(),
        reward_batch_repo=get_reward_batch_repo(),
        treasury_repo=get_treasury_repo(),
        outbox_repo=get_outbox_repo(),
        cache=get_cache(request),
    )
