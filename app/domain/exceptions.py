"""Domain-level exceptions for the finance service."""


class DomainError(Exception):
    """Base class for all domain errors."""


class InsufficientFunds(DomainError):
    """Raised when an account lacks sufficient balance for a debit."""


class DuplicateOperation(DomainError):
    """Raised when an idempotency key has already been used."""


class AccountNotFound(DomainError):
    """Raised when the requested account does not exist."""


class AccountInactive(DomainError):
    """Raised when an operation targets an inactive account."""


class CurrencyMismatch(DomainError):
    """Raised when currencies don't match in a transaction."""


class RuleAlreadyExists(DomainError):
    """Raised when a rule with the same event_code already exists."""


class AuthError(Exception):
    """Base class for authentication-related errors."""


class JwtValidationError(AuthError):
    """Raised when JWT bearer token validation fails."""


class JwtConfigurationError(AuthError):
    """Raised when JWT auth is enabled but configuration is invalid."""
