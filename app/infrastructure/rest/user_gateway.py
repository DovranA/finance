"""REST implementation of user-management lookups."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from app.core.config import UserManagementSettings
from app.domain.entities.user import User
from app.domain.repositories.user_gateway import UserGateway
from app.infrastructure.rest.client import AsyncRestApiClient


class RestUserGateway(UserGateway):
    def __init__(
        self,
        *,
        client: AsyncRestApiClient,
        settings: UserManagementSettings,
    ) -> None:
        self._client = client
        self._settings = settings

    async def list_users_by_ids(
        self,
        *,
        current_user_id: Optional[uuid.UUID],
        user_ids: list[uuid.UUID],
    ) -> list[User]:
        if not user_ids:
            return []

        payload = {
            "current_user_id": str(current_user_id) if current_user_id else None,
            "user_ids": [str(user_id) for user_id in user_ids],
        }
        headers = {"Content-Type": "application/json"}
        if self._settings.api_key:
            headers["X-API-KEY"] = self._settings.api_key

        response = await self._client.post(
            self._settings.users_lookup_path,
            json=payload,
            headers=headers,
            timeout_seconds=self._settings.timeout_seconds,
            base_url=self._settings.endpoint or None,
        )
        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: Any) -> list[User]:
        if not isinstance(response, dict):
            return []

        nodes = response.get("nodes")
        if not isinstance(nodes, list):
            return []

        users: list[User] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = node.get("id")
            if not node_id:
                continue

            try:
                parsed_id = uuid.UUID(str(node_id))
            except (ValueError, TypeError):
                continue

            users.append(
                User(
                    id=parsed_id,
                    username=str(node.get("username") or ""),
                    fullname=node.get("full_name"),
                    is_following=bool(node.get("is_following", False)),
                    role=str(node.get("role") or ""),
                )
            )

        return users
