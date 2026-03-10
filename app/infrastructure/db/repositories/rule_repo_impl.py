"""Concrete rule repository — raw asyncpg SQL."""

from __future__ import annotations

import uuid

import orjson
from asyncpg import Connection

from app.domain.entities.rule import Rule
from app.domain.repositories.rule_repo import RuleRepository


class PgRuleRepository(RuleRepository):

    async def get_by_id(self, rule_id: uuid.UUID, conn: Connection) -> Rule | None:
        row = await conn.fetchrow(
            "SELECT id, event_code, description, conditions, actions, "
            "priority, is_active, expired_at, created_at, updated_at "
            "FROM rules WHERE id = $1",
            rule_id,
        )
        return self._to_entity(row) if row else None

    async def get_by_event_code(self, event_code: str, conn: Connection) -> list[Rule]:
        rows = await conn.fetch(
            "SELECT id, event_code, description, conditions, actions, "
            "priority, is_active, expired_at, created_at, updated_at "
            "FROM rules WHERE event_code = $1 ORDER BY priority DESC",
            event_code,
        )
        return [self._to_entity(r) for r in rows]

    async def get_active_by_event_code(
        self, event_code: str, conn: Connection
    ) -> list[Rule]:
        rows = await conn.fetch(
            "SELECT id, event_code, description, conditions, actions, "
            "priority, is_active, expired_at, created_at, updated_at "
            "FROM rules "
            "WHERE event_code = $1 AND is_active = TRUE "
            "AND (expired_at IS NULL OR expired_at > NOW()) "
            "ORDER BY priority DESC",
            event_code,
        )
        return [self._to_entity(r) for r in rows]

    async def list_all(
        self, conn: Connection, limit: int = 50, offset: int = 0
    ) -> list[Rule]:
        rows = await conn.fetch(
            "SELECT id, event_code, description, conditions, actions, "
            "priority, is_active, expired_at, created_at, updated_at "
            "FROM rules ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
        return [self._to_entity(r) for r in rows]

    async def create(self, rule: Rule, conn: Connection) -> None:
        await conn.execute(
            "INSERT INTO rules "
            "(id, event_code, description, conditions, actions, "
            "priority, is_active, expired_at, created_at, updated_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
            rule.id,
            rule.event_code,
            rule.description,
            orjson.dumps(rule.conditions).decode(),
            orjson.dumps(rule.actions).decode(),
            rule.priority,
            rule.is_active,
            rule.expired_at,
            rule.created_at,
            rule.updated_at,
        )

    async def update(self, rule: Rule, conn: Connection) -> None:
        await conn.execute(
            "UPDATE rules SET event_code = $1, description = $2, "
            "conditions = $3, actions = $4, priority = $5, "
            "is_active = $6, expired_at = $7, updated_at = NOW() "
            "WHERE id = $8",
            rule.event_code,
            rule.description,
            orjson.dumps(rule.conditions).decode(),
            orjson.dumps(rule.actions).decode(),
            rule.priority,
            rule.is_active,
            rule.expired_at,
            rule.id,
        )

    async def delete(self, rule_id: uuid.UUID, conn: Connection) -> None:
        await conn.execute("DELETE FROM rules WHERE id = $1", rule_id)

    @staticmethod
    def _to_entity(row) -> Rule:
        conditions = row["conditions"]
        if isinstance(conditions, str):
            conditions = orjson.loads(conditions)
        actions = row["actions"]
        if isinstance(actions, str):
            actions = orjson.loads(actions)
        return Rule(
            id=row["id"],
            event_code=row["event_code"],
            description=row["description"],
            conditions=conditions,
            actions=actions,
            priority=row["priority"],
            is_active=row["is_active"],
            expired_at=row["expired_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
