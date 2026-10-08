"""Structured logging with correlation-ID support and request logging middleware."""

import contextvars
import json
import logging
import time
import uuid
from datetime import UTC, datetime

from starlette.types import ASGIApp, Message, Receive, Scope, Send

CORRELATION_HEADER = "X-Request-ID"
_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="-")

_STANDARD_RECORD_KEYS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}

logger = logging.getLogger("app.request")


def get_correlation_id() -> str:
    return _correlation_id.get()


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON including the correlation ID."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlationId": get_correlation_id(),
        }
        payload.update({k: v for k, v in record.__dict__.items() if k not in _STANDARD_RECORD_KEYS})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    logging.getLogger("uvicorn.access").disabled = True


class RequestLoggingMiddleware:
    """Pure ASGI middleware: assigns a correlation ID and logs method, path, status, duration."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        correlation_id = headers.get(CORRELATION_HEADER.lower()) or headers.get("x-correlation-id") or str(uuid.uuid4())
        token = _correlation_id.set(correlation_id)
        scope.setdefault("state", {})["correlation_id"] = correlation_id
        status_code = 500
        started = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message.setdefault("headers", []).append((CORRELATION_HEADER.lower().encode(), correlation_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "request completed",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "statusCode": status_code,
                    "durationMs": duration_ms,
                },
            )
            _correlation_id.reset(token)
