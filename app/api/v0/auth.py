"""JWT bearer authentication dependency for API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.core.config import get_settings
from app.domain.exceptions import JwtConfigurationError, JwtValidationError

bearer_scheme = HTTPBearer(auto_error=False)


def _parse_unix_ts(value: object, claim_name: str) -> int:
    if not isinstance(value, int):
        raise JwtValidationError(f"invalid {claim_name} claim")
    return value


def _validate_temporal_claims(exp: int, iat: int, leeway_seconds: int) -> None:
    now = int(datetime.now(tz=timezone.utc).timestamp())

    if exp + leeway_seconds < now:
        raise JwtValidationError("token expired")

    if iat - leeway_seconds > now:
        raise JwtValidationError("token issued in the future")


async def require_jwt_bearer(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    settings = get_settings()

    if not settings.jwt.enabled:
        return {}

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise JwtValidationError("missing bearer token")

    if not settings.jwt.secret_key:
        raise JwtConfigurationError("JWT_SECRET_KEY is not configured")

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.jwt.secret_key,
            algorithms=[settings.jwt.algorithm],
            options={"verify_exp": False, "verify_iat": False},
        )
    except InvalidTokenError as exc:
        raise JwtValidationError("invalid bearer token") from exc

    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise JwtValidationError("invalid sub claim")

    try:
        UUID(sub)
    except ValueError as exc:
        raise JwtValidationError("sub must be a valid UUID") from exc

    device_id = payload.get("device_id")
    if not isinstance(device_id, str):
        raise JwtValidationError("invalid device_id claim")
    try:
        UUID(device_id)
    except ValueError as exc:
        raise JwtValidationError("device_id must be a valid UUID") from exc

    role = payload.get("role")
    if not isinstance(role, str) or not role.strip():
        raise JwtValidationError("invalid role claim")

    exp = _parse_unix_ts(payload.get("exp"), "exp")
    iat = _parse_unix_ts(payload.get("iat"), "iat")
    _validate_temporal_claims(
        exp=exp, iat=iat, leeway_seconds=settings.jwt.leeway_seconds
    )

    return payload
