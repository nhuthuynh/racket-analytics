"""Structured JSON logs to stdout with correlation fields (ST-005; AQS/OPS-03, NFR-076b, NFR-069).

Every line has ``ts`` (UTC, ``Z``), ``level``, ``logger``, ``msg``, ``trace_id``, ``request_id``
and the pseudonymous ``user_id`` (an account UUID, never a name or email). Fields passed via
``extra=`` are added as they are; callers must never pass personal data, titles, tokens or URLs.
Chatty third-party loggers that can print signed URLs or headers are capped at WARNING.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from opentelemetry import trace

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)

SECURITY_LOGGER = "racket.security"
# Loggers that can emit request URLs, signatures or headers at DEBUG/INFO.
QUIET_LOGGERS = ("botocore", "boto3", "s3transfer", "urllib3", "httpcore", "httpx", "asyncio")

_STANDARD = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "taskName"}
_HANDLER_NAME = "racket-json-stdout"


def current_trace_id() -> str | None:
    ctx = trace.get_current_span().get_span_context()
    return format(ctx.trace_id, "032x") if ctx.is_valid else None


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "trace_id": current_trace_id(),
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD and key not in payload:
                payload[key] = value
        if record.exc_info and record.exc_info[0] is not None:
            # The exception type only: messages can hold input or internals (AQS/SEC-04).
            payload["exc_type"] = record.exc_info[0].__name__
        return json.dumps(payload, default=str)


class StdoutHandler(logging.StreamHandler):  # type: ignore[type-arg]
    """Writes to whatever ``sys.stdout`` is at emit time (survives stdout redirection)."""

    def __init__(self) -> None:
        super().__init__(sys.stdout)

    @property
    def stream(self) -> Any:
        return sys.stdout

    @stream.setter
    def stream(self, value: Any) -> None:
        pass


def configure_logging(level: str = "INFO") -> None:
    """Idempotent: installs one JSON handler on the root logger."""
    root = logging.getLogger()
    if not any(getattr(h, "name", None) == _HANDLER_NAME for h in root.handlers):
        handler = StdoutHandler()
        handler.name = _HANDLER_NAME
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    root.setLevel(level)
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    # uvicorn's access log repeats the URL; our request log replaces it.
    logging.getLogger("uvicorn.access").disabled = True
