"""Cross-cutting schemas shared across all routes."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "finance-service"


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
