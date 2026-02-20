"""Concrete economic action repository — raw asyncpg SQL."""

from __future__ import annotations

import uuid

from asyncpg import Connection

from app.domain.entities.economic_action import EconomicAction, EconomicActionVersion
from app.domain.repositories.economic_action_repo import EconomicActionRepository


class PgEconomicActionRepository(EconomicActionRepository):

    async def create_action(
        self, action: EconomicAction, conn: Connection
    ) -> None:
        await conn.execute(
            "INSERT INTO economic_actions (id, code, description, is_active, created_at) "
            "VALUES ($1, $2, $3, $4, $5)",
            action.id,
            action.code,
            action.description,
            action.is_active,
            action.created_at,
        )

    async def get_action_by_id(
        self, action_id: uuid.UUID, conn: Connection
    ) -> EconomicAction | None:
        row = await conn.fetchrow(
            "SELECT id, code, description, is_active, created_at "
            "FROM economic_actions WHERE id = $1",
            action_id,
        )
        return self._action_to_entity(row) if row else None

    async def get_action_by_code(
        self, code: str, conn: Connection
    ) -> EconomicAction | None:
        row = await conn.fetchrow(
            "SELECT id, code, description, is_active, created_at "
            "FROM economic_actions WHERE code = $1",
            code.upper(),
        )
        return self._action_to_entity(row) if row else None

    async def list_actions(self, conn: Connection) -> list[EconomicAction]:
        rows = await conn.fetch(
            "SELECT id, code, description, is_active, created_at "
            "FROM economic_actions ORDER BY created_at"
        )
        return [self._action_to_entity(r) for r in rows]

    async def set_active(
        self, action_id: uuid.UUID, is_active: bool, conn: Connection
    ) -> None:
        await conn.execute(
            "UPDATE economic_actions SET is_active = $1 WHERE id = $2",
            is_active,
            action_id,
        )

    # ── Versions ──────────────────────────────────────────

    async def create_version(
        self, version: EconomicActionVersion, conn: Connection
    ) -> None:
        await conn.execute(
            "INSERT INTO economic_action_versions "
            "(id, action_id, publisher_reward, actor_reward, platform_fee, "
            "treasury_cut, version, is_active, active_from, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
            version.id,
            version.action_id,
            version.publisher_reward,
            version.actor_reward,
            version.platform_fee,
            version.treasury_cut,
            version.version,
            version.is_active,
            version.active_from,
            version.created_at,
        )

    async def get_active_version(
        self, action_code: str, conn: Connection
    ) -> EconomicActionVersion | None:
        row = await conn.fetchrow(
            "SELECT v.id, v.action_id, v.publisher_reward, v.actor_reward, "
            "v.platform_fee, v.treasury_cut, v.version, v.is_active, "
            "v.active_from, v.created_at "
            "FROM economic_action_versions v "
            "JOIN economic_actions a ON a.id = v.action_id "
            "WHERE a.code = $1 AND a.is_active = TRUE AND v.is_active = TRUE",
            action_code.upper(),
        )
        return self._version_to_entity(row) if row else None

    async def activate_version(
        self, version_id: uuid.UUID, action_id: uuid.UUID, conn: Connection
    ) -> None:
        # Deactivate all versions for this action
        await conn.execute(
            "UPDATE economic_action_versions SET is_active = FALSE "
            "WHERE action_id = $1",
            action_id,
        )
        # Activate the target version
        await conn.execute(
            "UPDATE economic_action_versions "
            "SET is_active = TRUE, active_from = NOW() "
            "WHERE id = $1",
            version_id,
        )

    async def get_next_version_number(
        self, action_id: uuid.UUID, conn: Connection
    ) -> int:
        row = await conn.fetchrow(
            "SELECT COALESCE(MAX(version), 0) + 1 AS next_version "
            "FROM economic_action_versions WHERE action_id = $1",
            action_id,
        )
        return row["next_version"]

    async def list_versions(
        self, action_id: uuid.UUID, conn: Connection
    ) -> list[EconomicActionVersion]:
        rows = await conn.fetch(
            "SELECT id, action_id, publisher_reward, actor_reward, "
            "platform_fee, treasury_cut, version, is_active, active_from, created_at "
            "FROM economic_action_versions WHERE action_id = $1 "
            "ORDER BY version",
            action_id,
        )
        return [self._version_to_entity(r) for r in rows]

    # ── Mappers ───────────────────────────────────────────

    @staticmethod
    def _action_to_entity(row) -> EconomicAction:
        return EconomicAction(
            id=row["id"],
            code=row["code"],
            description=row["description"],
            is_active=row["is_active"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _version_to_entity(row) -> EconomicActionVersion:
        return EconomicActionVersion(
            id=row["id"],
            action_id=row["action_id"],
            publisher_reward=row["publisher_reward"],
            actor_reward=row["actor_reward"],
            platform_fee=row["platform_fee"],
            treasury_cut=row["treasury_cut"],
            version=row["version"],
            is_active=row["is_active"],
            active_from=row["active_from"],
            created_at=row["created_at"],
        )
