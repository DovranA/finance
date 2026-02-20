"""Actor action repository interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from asyncpg import Connection

from app.domain.entities.actor_action import ActorAction


class ActorActionRepository(ABC):

    @abstractmethod
    async def create(self, action: ActorAction, conn: Connection) -> None:
        ...
