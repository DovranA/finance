"""Transaction domain entity — wraps the `transactions` table."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def generate_idempotency_key(*parts: str | uuid.UUID | None) -> str:
    """Build a deterministic idempotency key from any number of components.

    Same inputs always produce the same key.  ``None`` values are skipped.

    Examples::

        generate_idempotency_key("like", account_id, post_id)
        generate_idempotency_key("transfer", from_id, to_id, amount)
        generate_idempotency_key("repost", user_id, content_id)
    """
    filtered = [str(p) for p in parts if p is not None]
    if not filtered:
        return str(uuid.uuid4())
    raw = ":".join(filtered)
    return hashlib.sha256(raw.encode()).hexdigest()


def resolve_idempotency_pattern(pattern: str, context: dict[str, Any]) -> str:
    """Resolve an idempotency pattern using context values and hash the result.

    Pattern example: ``"{event_code}:{user_id}:{event_id}"``

    All ``{placeholder}`` tokens are replaced with values from *context*.
    Missing keys are replaced with the literal string ``'none'``.
    The resolved string is then SHA-256 hashed for a fixed-length key.
    """
    import re

    def _replacer(match: re.Match) -> str:
        key = match.group(1)
        val = context.get(key)
        return str(val) if val is not None else "none"

    resolved = re.sub(r"\{(\w+)\}", _replacer, pattern)
    return hashlib.sha256(resolved.encode()).hexdigest()


@dataclass(frozen=True)
class Transaction:
    """Represents a financial transaction with idempotency guarantees.

    Maps 1-to-1 with the `transactions` table.
    """

    id: uuid.UUID
    idempotency_key: str
    status: str  # 'pending', 'completed', 'failed'
    reference_type: str | None = None
    reference_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None

    @classmethod
    def generate_key(cls, *parts: str | uuid.UUID | None) -> str:
        """Delegate to the universal generator."""
        return generate_idempotency_key(*parts)

    @classmethod
    def create(
        cls,
        *,
        idempotency_key: str,
        status: str = "pending",
        reference_type: str | None = None,
        reference_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
    ) -> Transaction:
        if not idempotency_key:
            raise ValueError("Idempotency key must not be empty")
        return cls(
            id=uuid.uuid4(),
            idempotency_key=idempotency_key,
            status=status,
            reference_type=reference_type,
            reference_id=reference_id,
            metadata=metadata or {},
            expires_at=expires_at,
        )
