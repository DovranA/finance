"""Reusable async REST API client for use cases."""

from __future__ import annotations

from typing import Any

import httpx


class RestApiError(Exception):
    """Raised when an upstream REST call fails."""

    def __init__(self, status_code: int, method: str, url: str, detail: str) -> None:
        self.status_code = status_code
        self.method = method
        self.url = url
        self.detail = detail
        super().__init__(f"{method} {url} failed with {status_code}: {detail}")


class AsyncRestApiClient:
    """Thin wrapper around httpx.AsyncClient with JSON-first helpers."""

    def __init__(
        self,
        *,
        base_url: str = "",
        timeout_seconds: float = 10.0,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout_seconds),
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
            ),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _resolve_url(path: str, base_url: str | None = None) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if base_url:
            return f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        return path

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
        base_url: str | None = None,
    ) -> Any:
        url = self._resolve_url(path, base_url)
        response = await self._client.request(
            method=method,
            url=url,
            params=params,
            json=json,
            headers=headers,
            timeout=timeout_seconds,
        )

        if response.is_error:
            raise RestApiError(
                status_code=response.status_code,
                method=method.upper(),
                url=str(response.request.url),
                detail=response.text,
            )

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.text

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
        base_url: str | None = None,
    ) -> Any:
        return await self.request(
            "GET",
            path,
            params=params,
            headers=headers,
            timeout_seconds=timeout_seconds,
            base_url=base_url,
        )

    async def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
        base_url: str | None = None,
    ) -> Any:
        return await self.request(
            "POST",
            path,
            params=params,
            json=json,
            headers=headers,
            timeout_seconds=timeout_seconds,
            base_url=base_url,
        )

    async def put(
        self,
        path: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
        base_url: str | None = None,
    ) -> Any:
        return await self.request(
            "PUT",
            path,
            params=params,
            json=json,
            headers=headers,
            timeout_seconds=timeout_seconds,
            base_url=base_url,
        )

    async def patch(
        self,
        path: str,
        *,
        json: dict[str, Any] | list[Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
        base_url: str | None = None,
    ) -> Any:
        return await self.request(
            "PATCH",
            path,
            params=params,
            json=json,
            headers=headers,
            timeout_seconds=timeout_seconds,
            base_url=base_url,
        )

    async def delete(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
        base_url: str | None = None,
    ) -> Any:
        return await self.request(
            "DELETE",
            path,
            params=params,
            headers=headers,
            timeout_seconds=timeout_seconds,
            base_url=base_url,
        )
