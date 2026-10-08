"""Centralized exception -> error-envelope translation."""

import logging
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

_HTTP_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
}


def _correlation_id(request: Request) -> str | None:
    return getattr(request.state, "correlation_id", None)


def error_body(
    request: Request,
    message: str,
    error_code: str,
    errors: dict[str, list[str]] | None = None,
) -> dict:
    body: dict = {
        "success": False,
        "message": message,
        "errorCode": error_code,
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "path": request.url.path,
        "correlationId": _correlation_id(request),
    }
    if errors:
        body["errors"] = errors
    return body


def _field_name(location: tuple) -> str:
    parts = [str(part) for part in location if part not in ("body", "query", "path", "header")]
    return ".".join(parts) or "request"


def _collect_validation_errors(exc: RequestValidationError) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    for item in exc.errors():
        message = str(item["msg"]).removeprefix("Value error, ")
        errors.setdefault(_field_name(item["loc"]), []).append(message)
    return errors


async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error("application error: %s", exc.message, exc_info=exc)
    else:
        logger.info("request rejected", extra={"errorCode": exc.error_code, "reason": exc.message})
    body = error_body(request, exc.message, exc.error_code, exc.errors)
    return JSONResponse(status_code=exc.status_code, content=body)


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    body = error_body(request, "Validation failed", "VALIDATION_ERROR", _collect_validation_errors(exc))
    return JSONResponse(status_code=422, content=body)


async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_ERROR_CODES.get(exc.status_code, "HTTP_ERROR")
    body = error_body(request, str(exc.detail), code)
    return JSONResponse(status_code=exc.status_code, content=body, headers=getattr(exc, "headers", None))


async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("integrity violation", extra={"reason": type(exc.orig).__name__})
    body = error_body(request, "Operation violates a data integrity constraint", "CONFLICT")
    return JSONResponse(status_code=409, content=body)


async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled exception", exc_info=exc)
    body = error_body(request, "An unexpected error occurred", "INTERNAL_ERROR")
    return JSONResponse(status_code=500, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, handle_app_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(IntegrityError, handle_integrity_error)
    app.add_exception_handler(Exception, handle_unexpected_exception)
