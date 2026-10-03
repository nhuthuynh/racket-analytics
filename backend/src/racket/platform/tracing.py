"""OpenTelemetry tracing with W3C Trace Context (ST-005, ST-007; AQS/OPS-06, NFR-076).

* The app and the worker use the **global** tracer provider. They install an SDK provider only
  when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set and no provider exists yet, so tests can install
  an in-memory exporter first (``tests/conftest.py``).
* Incoming ``traceparent`` headers are validated strictly before use. Anything malformed or
  oversized is ignored and the request starts a new trace (IT-00-12).
* The trace context travels with a job as a W3C carrier dict (enqueue → worker).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

from opentelemetry import context as otel_context
from opentelemetry import propagate, trace
from opentelemetry.trace import Tracer

log = logging.getLogger(__name__)

TRACER_NAME = "racket"
MAX_HEADER = 512
_TRACEPARENT = re.compile(r"([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})(-.*)?")
_ZERO_TRACE = "0" * 32
_ZERO_SPAN = "0" * 16


def tracer() -> Tracer:
    return trace.get_tracer(TRACER_NAME)


def valid_traceparent(value: str | None) -> bool:
    """W3C Trace Context level 1 rules, plus a size cap (lower-case hex only)."""
    if not value or len(value) > MAX_HEADER:
        return False
    match = _TRACEPARENT.fullmatch(value)
    if match is None:
        return False
    version, trace_id, span_id, _flags, rest = match.groups()
    if version == "ff" or trace_id == _ZERO_TRACE or span_id == _ZERO_SPAN:
        return False
    return not (version == "00" and rest)


def extract_context(headers: Mapping[str, str]) -> otel_context.Context | None:
    """The remote parent context from request headers or a job carrier, or ``None``."""
    traceparent = headers.get("traceparent")
    if not valid_traceparent(traceparent):
        return None
    carrier = {"traceparent": str(traceparent)}
    tracestate = headers.get("tracestate")
    if tracestate and len(tracestate) <= MAX_HEADER:
        carrier["tracestate"] = tracestate
    try:
        return propagate.extract(carrier)
    except Exception:  # noqa: BLE001 - a broken tracestate must never fail the request
        return propagate.extract({"traceparent": str(traceparent)})


def inject_current() -> dict[str, str]:
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    return carrier


def configure_tracing(service_name: str, otlp_endpoint: str | None) -> None:
    if not otlp_endpoint:
        return
    if not isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
        return  # someone (a test, an operator) already installed one; never replace it
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import-not-found,unused-ignore]
            OTLPSpanExporter,
        )
    except ImportError:
        log.warning("tracing.exporter_unavailable", extra={"event": "tracing.exporter_unavailable"})
        return
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces"))
    )
    trace.set_tracer_provider(provider)


def attach(ctx: otel_context.Context | None) -> Any:
    return otel_context.attach(ctx) if ctx is not None else None


def detach(token: Any) -> None:
    if token is not None:
        otel_context.detach(token)
