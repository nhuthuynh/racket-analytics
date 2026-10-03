"""HTTP edge: one ASGI middleware and the central exception handlers (ST-005).

``EdgeMiddleware`` wraps every request. It
* assigns the request ID (an incoming ``X-Request-ID`` only if it is safe, ASVS 16.4.1);
* opens the SERVER span, continuing a valid W3C ``traceparent`` or starting a new trace;
* refuses state-changing requests from an origin outside ``ALLOWED_ORIGINS`` (403);
* adds the security headers to every response (NFR-061, NFR-067; api-sprint-00 §1.1);
* turns any exception that escapes the app into the generic 500 body (AQS/SEC-12), so even
  a crash gets the headers, a ``support_ref`` and a log line with the same reference;
* logs one JSON line per request with the route template, never the raw path or query.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from opentelemetry.trace import SpanKind, Status, StatusCode
from starlette.exceptions import HTTPException as StarletteHTTPException

from racket.platform.errors import AppError, ErrorMapper, ErrorResponse, ForbiddenOrigin
from racket.platform.logs import request_id_var, user_id_var
from racket.platform.tracing import extract_context, tracer

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

log = logging.getLogger("racket.http")
_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
_STATE_CHANGING = {"POST", "PUT", "PATCH", "DELETE"}
SECURITY_HEADERS = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    # Stricter than api-sprint-00 §1.1 (which requires it on authenticated, error and tus
    # responses): the API serves nothing that a cache should keep (judgment).
    (b"cache-control", b"no-store"),
)
_OWNED_HEADERS = {name for name, _ in SECURITY_HEADERS} | {b"server", b"x-request-id"}


ERROR_HEADERS_STATE = "error_headers"


def route_error_headers(request: Request) -> dict[str, str]:
    """Headers a route group asks for on its error responses too, set on ``request.state``
    by a router dependency (e.g. tus: every tus response carries ``Tus-Resumable``)."""
    return dict(getattr(request.state, ERROR_HEADERS_STATE, None) or {})


def error_response(
    error: ErrorResponse, method: str, extra_headers: dict[str, str] | None = None
) -> Response:
    headers = {**(extra_headers or {}), **error.headers}
    if method == "HEAD":  # HEAD responses carry no body (api-sprint-00 §3)
        return Response(status_code=error.status, headers=headers)
    return JSONResponse(error.body(), status_code=error.status, headers=headers)


def log_error(error: ErrorResponse, exc: BaseException | None) -> None:
    extra = {"event": "http.error", "status": error.status, "code": error.code,
             "support_ref": error.support_ref}  # fmt: skip
    if error.status >= 500:
        log.error("request failed", extra=extra, exc_info=exc)
    else:
        log.info("request refused", extra=extra)


def install_error_handlers(app: FastAPI, mapper: ErrorMapper) -> None:
    async def on_app_error(request: Request, exc: Exception) -> Response:
        error = mapper.map(exc)
        log_error(error, exc)
        return error_response(error, request.method, route_error_headers(request))

    async def on_http_error(request: Request, exc: Exception) -> Response:
        status = exc.status_code if isinstance(exc, StarletteHTTPException) else 500
        error = mapper.for_status(status)
        log_error(error, None)
        return error_response(error, request.method, route_error_headers(request))

    async def on_validation_error(request: Request, exc: Exception) -> Response:
        error = mapper.for_status(422)  # never echo the input (NFR-058)
        log_error(error, None)
        return error_response(error, request.method, route_error_headers(request))

    app.add_exception_handler(AppError, on_app_error)
    app.add_exception_handler(StarletteHTTPException, on_http_error)
    app.add_exception_handler(RequestValidationError, on_validation_error)


class EdgeMiddleware:
    def __init__(
        self, app: ASGIApp, mapper: ErrorMapper, allowed_origins: tuple[str, ...] = ()
    ) -> None:
        self.app = app
        self.mapper = mapper
        self.allowed_origins = set(allowed_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        method = str(scope["method"])
        incoming_id = headers.get("x-request-id", "")
        request_id = incoming_id if _SAFE_REQUEST_ID.fullmatch(incoming_id) else uuid.uuid4().hex
        rid_token = request_id_var.set(request_id)
        uid_token = user_id_var.set(None)
        started = time.monotonic()
        status_holder = {"status": 500, "started": False}

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                status_holder["started"] = True
                raw = [
                    (k, v) for k, v in message.get("headers", []) if k.lower() not in _OWNED_HEADERS
                ]
                raw += [*SECURITY_HEADERS, (b"x-request-id", request_id.encode())]
                message["headers"] = raw
            await send(message)

        span_ctx = extract_context(headers)
        with tracer().start_as_current_span(method, context=span_ctx, kind=SpanKind.SERVER) as span:
            try:
                origin = headers.get("origin")
                if (
                    self.allowed_origins
                    and method in _STATE_CHANGING
                    and origin is not None
                    and origin not in self.allowed_origins
                ):
                    raise ForbiddenOrigin("origin not allowed")
                await self.app(scope, receive, send_with_headers)
            except Exception as exc:  # noqa: BLE001 - the global fallback (AQS/SEC-12)
                error = self.mapper.map(exc)
                log_error(error, exc)
                if not status_holder["started"]:
                    response = error_response(error, method)
                    await response(scope, receive, send_with_headers)
                span.set_status(Status(StatusCode.ERROR))
            finally:
                route = scope.get("route")
                template = getattr(route, "path", None) or "unmatched"
                span.update_name(f"{method} {template}")
                span.set_attribute("http.request.method", method)
                span.set_attribute("http.route", template)
                span.set_attribute("http.response.status_code", int(status_holder["status"]))
                log.info(
                    "request",
                    extra={
                        "event": "http.request",
                        "method": method,
                        "route": template,
                        "status": status_holder["status"],
                        "duration_ms": round((time.monotonic() - started) * 1000, 1),
                    },
                )
                user_id_var.reset(uid_token)
                request_id_var.reset(rid_token)
