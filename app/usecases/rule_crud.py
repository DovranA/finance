"""CRUD use cases for rules management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from asyncpg import Pool
from asyncpg.exceptions import UniqueViolationError

from app.domain.entities.rule import Rule
from app.domain.exceptions import DomainError, RuleAlreadyExists
from app.domain.repositories.rule_repo import RuleRepository
from app.infrastructure.db.transaction import transaction
from app.infrastructure.redis.cache import CacheService


class RuleNotFound(DomainError):
    """Raised when the requested rule does not exist."""


class CreateRuleUseCase:
    def __init__(
        self, pool: Pool, rule_repo: RuleRepository, cache: CacheService | None = None
    ) -> None:
        self._pool = pool
        self._rule_repo = rule_repo
        self._cache = cache

    async def execute(
        self,
        *,
        event_code: str,
        conditions: dict | None = None,
        actions: dict | None = None,
        description: str | None = None,
        description_i18n: dict[str, str] | None = None,
        priority: int = 0,
        expired_at: datetime | None = None,
    ) -> Rule:

        rule = Rule.create(
            event_code=event_code,
            conditions=conditions,
            actions=actions,
            description=description,
            description_i18n=description_i18n,
            priority=priority,
            expired_at=expired_at,
        )
        try:
            async with transaction(self._pool) as conn:
                await self._rule_repo.create(rule, conn)
        except UniqueViolationError:
            raise RuleAlreadyExists(
                f"Rule with event_code '{event_code}' already exists"
            )
        if self._cache:
            await self._cache.invalidate_rules(event_code)
        return rule


class GetRuleUseCase:
    def __init__(self, pool: Pool, rule_repo: RuleRepository) -> None:
        self._pool = pool
        self._rule_repo = rule_repo

    async def execute(self, *, rule_id: uuid.UUID) -> Rule:
        async with transaction(self._pool) as conn:
            rule = await self._rule_repo.get_by_id(rule_id, conn)
        if rule is None:
            raise RuleNotFound(f"Rule {rule_id} not found")
        return rule


class ListRulesUseCase:
    def __init__(self, pool: Pool, rule_repo: RuleRepository) -> None:
        self._pool = pool
        self._rule_repo = rule_repo

    async def execute(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Rule]:
        async with transaction(self._pool) as conn:
            return await self._rule_repo.list_all(conn, limit=limit, offset=offset)


class UpdateRuleUseCase:
    def __init__(
        self, pool: Pool, rule_repo: RuleRepository, cache: CacheService | None = None
    ) -> None:
        self._pool = pool
        self._rule_repo = rule_repo
        self._cache = cache

    async def execute(
        self,
        *,
        rule_id: uuid.UUID,
        event_code: str | None = None,
        conditions: dict | None = None,
        actions: dict | None = None,
        description: str | None = None,
        description_i18n: dict[str, str] | None = None,
        priority: int | None = None,
        is_active: bool | None = None,
        expired_at: datetime | None = None,
    ) -> Rule:
        async with transaction(self._pool) as conn:
            rule = await self._rule_repo.get_by_id(rule_id, conn)
            if rule is None:
                raise RuleNotFound(f"Rule {rule_id} not found")

            if event_code is not None:
                rule.event_code = event_code
            if conditions is not None:
                rule.conditions = conditions
            if actions is not None:
                rule.actions = actions
            if description is not None:
                rule.description = description
            if description_i18n is not None:
                rule.description_i18n = description_i18n
            if priority is not None:
                rule.priority = priority
            if is_active is not None:
                rule.is_active = is_active
            if expired_at is not None:
                rule.expired_at = expired_at

            rule.updated_at = datetime.now(timezone.utc)
            try:
                await self._rule_repo.update(rule, conn)
            except UniqueViolationError:
                raise RuleAlreadyExists(
                    f"Rule with event_code '{rule.event_code}' already exists"
                )
        if self._cache:
            await self._cache.invalidate_rules(rule.event_code)
        return rule


class DeleteRuleUseCase:
    def __init__(
        self, pool: Pool, rule_repo: RuleRepository, cache: CacheService | None = None
    ) -> None:
        self._pool = pool
        self._rule_repo = rule_repo
        self._cache = cache

    async def execute(self, *, rule_id: uuid.UUID) -> None:
        async with transaction(self._pool) as conn:
            rule = await self._rule_repo.get_by_id(rule_id, conn)
            if rule is None:
                raise RuleNotFound(f"Rule {rule_id} not found")
            await self._rule_repo.delete(rule_id, conn)
        if self._cache:
            await self._cache.invalidate_rules(rule.event_code)
