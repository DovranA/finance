"""Concrete actor action repository — raw asyncpg SQL."""

from __future__ import annotations

from asyncpg import Connection

from app.domain.entities.actor_action import ActorAction
from app.domain.repositories.actor_action_repo import ActorActionRepository


class PgActorActionRepository(ActorActionRepository):

    async def create(self, action: ActorAction, conn: Connection) -> None:
        await conn.execute(
            "INSERT INTO actor_actions "
            "(id, actor_id, content_id, action_code, economic_version_id, reward_amount, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7)",
            action.id,
            action.actor_id,
            action.content_id,
            action.action_code,
            action.economic_version_id,
            action.reward_amount,
            action.created_at,
        )
