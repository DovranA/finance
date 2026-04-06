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
            "SELECT id, event_code, description_i18n, conditions, actions, tags, "
            "priority, is_active, expired_at, created_at, updated_at "
            "FROM rules WHERE id = $1",
            rule_id,
        )
        return self._to_entity(row) if row else None

    async def get_by_event_code(self, event_code: str, conn: Connection) -> list[Rule]:
        rows = await conn.fetch(
            "SELECT id, event_code, description_i18n, conditions, actions, tags, "
            "priority, is_active, expired_at, created_at, updated_at "
            "FROM rules WHERE event_code = $1 ORDER BY priority DESC",
            event_code,
        )
        return [self._to_entity(r) for r in rows]

    async def get_active_by_event_code(
        self, event_code: str, conn: Connection
    ) -> Rule | None:
        row = await conn.fetchrow(
            "SELECT id, event_code, description_i18n, conditions, actions, tags, "
            "priority, is_active, expired_at, created_at, updated_at "
            "FROM rules "
            "WHERE event_code = $1 AND is_active = TRUE "
            "AND (expired_at IS NULL OR expired_at > NOW()) "
            "ORDER BY priority DESC LIMIT 1",
            event_code,
        )
        return self._to_entity(row) if row else None

    async def list_all(
        self,
        conn: Connection,
        limit: int = 50,
        offset: int = 0,
        tags: list[str] | None = None,
    ) -> list[Rule]:
        if tags:
            rows = await conn.fetch(
                "SELECT id, event_code, description_i18n, conditions, actions, tags, "
                "priority, is_active, expired_at, created_at, updated_at "
                "FROM rules WHERE tags && $3::text[] ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                limit,
                offset,
                tags,
            )
        else:
            rows = await conn.fetch(
                "SELECT id, event_code, description_i18n, conditions, actions, tags, "
                "priority, is_active, expired_at, created_at, updated_at "
                "FROM rules ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                limit,
                offset,
            )
        return [self._to_entity(r) for r in rows]

    async def count(self, conn, tags: list[str] | None = None):
        if tags:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM rules WHERE tags && $1::text[]",
                tags,
            )
        return await conn.fetchval("SELECT COUNT(*) FROM rules")

    async def create(self, rule: Rule, conn: Connection) -> None:

        await conn.execute(
            "INSERT INTO rules "
            "(id, event_code, description_i18n, conditions, actions, tags, "
            "priority, is_active, expired_at, created_at, updated_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)",
            rule.id,
            rule.event_code,
            orjson.dumps(rule.description_i18n or {}).decode(),
            orjson.dumps(rule.conditions).decode(),
            orjson.dumps(rule.actions).decode(),
            rule.tags,
            rule.priority,
            rule.is_active,
            rule.expired_at,
            rule.created_at,
            rule.updated_at,
        )

    async def update(self, rule: Rule, conn: Connection) -> None:
        await conn.execute(
            "UPDATE rules SET event_code = $1, "
            "description_i18n = $2, conditions = $3, actions = $4, tags = $5, priority = $6, "
            "is_active = $7, expired_at = $8, updated_at = NOW() "
            "WHERE id = $9",
            rule.event_code,
            orjson.dumps(rule.description_i18n or {}).decode(),
            orjson.dumps(rule.conditions).decode(),
            orjson.dumps(rule.actions).decode(),
            rule.tags,
            rule.priority,
            rule.is_active,
            rule.expired_at,
            rule.id,
        )

    async def delete(self, rule_id: uuid.UUID, conn: Connection) -> None:
        await conn.execute("DELETE FROM rules WHERE id = $1", rule_id)

    @staticmethod
    def _to_entity(row) -> Rule:
        description_i18n = row.get("description_i18n")
        if isinstance(description_i18n, str):
            description_i18n = orjson.loads(description_i18n)
        conditions = row["conditions"]
        if isinstance(conditions, str):
            conditions = orjson.loads(conditions)
        actions = row["actions"]
        if isinstance(actions, str):
            actions = orjson.loads(actions)
        return Rule(
            id=row["id"],
            event_code=row["event_code"],
            description_i18n=description_i18n,
            conditions=conditions,
            actions=actions,
            tags=row.get("tags") or [],
            priority=row["priority"],
            is_active=row["is_active"],
            expired_at=row["expired_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
