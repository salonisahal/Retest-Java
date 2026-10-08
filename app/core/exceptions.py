"""Domain exceptions translated into the error envelope by the global handlers."""


class AppException(Exception):
    """Base class for all expected, client-facing application errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, errors: dict[str, list[str]] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors


class BadRequestError(AppException):
    status_code = 400
    error_code = "BAD_REQUEST"


class UnauthorizedError(AppException):
    status_code = 401
    error_code = "UNAUTHORIZED"


class ForbiddenError(AppException):
    status_code = 403
    error_code = "FORBIDDEN"


class NotFoundError(AppException):
    status_code = 404
    error_code = "NOT_FOUND"


class ConflictError(AppException):
    status_code = 409
    error_code = "CONFLICT"


class ValidationFailedError(AppException):
    """Business-rule validation failure reported as 422 with per-field errors."""

    status_code = 422
    error_code = "VALIDATION_ERROR"

    def __init__(self, message: str = "Validation failed", *, errors: dict[str, list[str]] | None = None) -> None:
        super().__init__(message, errors=errors)
