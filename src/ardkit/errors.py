"""Error types shared across ardkit.

``ArdError`` carries an ARD wire ``errorCode`` (the uppercase classification from
the registry OpenAPI: ``INVALID_ARGUMENT``, ``UNAUTHENTICATED``, ``NOT_FOUND``,
``RATE_LIMIT_EXCEEDED``, ``INTERNAL_ERROR``, ``NOT_IMPLEMENTED``) and the HTTP
status the registry layer should map it to.
"""

from __future__ import annotations


class ArdError(Exception):
    """Base class for ardkit errors carrying an ARD wire error code."""

    error_code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(
        self, message: str, *, error_code: str | None = None, http_status: int | None = None
    ):
        super().__init__(message)
        self.message = message
        if error_code is not None:
            self.error_code = error_code
        if http_status is not None:
            self.http_status = http_status

    def to_wire(self) -> dict[str, str]:
        """Render the spec ``Error`` object: ``{errorCode, message}``."""
        return {"errorCode": self.error_code, "message": self.message}


class InvalidArgument(ArdError):
    error_code = "INVALID_ARGUMENT"
    http_status = 400


class Unauthenticated(ArdError):
    error_code = "UNAUTHENTICATED"
    http_status = 401


class NotFound(ArdError):
    error_code = "NOT_FOUND"
    http_status = 404


class RateLimitExceeded(ArdError):
    error_code = "RATE_LIMIT_EXCEEDED"
    http_status = 429


class NotImplementedByServer(ArdError):
    error_code = "NOT_IMPLEMENTED"
    http_status = 501


class ValidationError(ArdError):
    """Raised when a manifest fails JSON Schema conformance validation."""

    error_code = "INVALID_ARGUMENT"
    http_status = 400

    def __init__(self, message: str, *, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


__all__ = [
    "ArdError",
    "InvalidArgument",
    "Unauthenticated",
    "NotFound",
    "RateLimitExceeded",
    "NotImplementedByServer",
    "ValidationError",
]
