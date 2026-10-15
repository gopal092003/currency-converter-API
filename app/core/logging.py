"""Structured logging configuration for the application."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings

_RESERVED_RECORD_FIELDS = set(logging.makeLogRecord({}).__dict__.keys()) | {
    "message",
    "asctime",
}


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(UTC).isoformat()

        payload: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": settings.app_env,
            "service": settings.app_name,
        }

        # Support structured fields passed via logger.info(..., extra={...}).
        for key, value in record.__dict__.items():
            if (
                key not in _RESERVED_RECORD_FIELDS
                and not key.startswith("_")
                and key not in payload
            ):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(
            payload,
            default=str,
            ensure_ascii=False,
        )


class DevelopmentFormatter(logging.Formatter):
    """Readable console formatter for local development."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)

        request_id = getattr(record, "request_id", None)
        if request_id:
            base = f"{base} request_id={request_id}"

        return base


def configure_logging() -> None:
    """Configure root logging once during application startup."""

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    if settings.app_env == "development" and not settings.testing:
        handler.setFormatter(
            DevelopmentFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
    else:
        handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Keep framework logs consistent with application logs.
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        framework_logger = logging.getLogger(logger_name)
        framework_logger.handlers.clear()
        framework_logger.propagate = True

    logging.captureWarnings(True)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
