"""Span queries over the in-memory exporter (AQS/OPS-06)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from opentelemetry.trace import SpanKind

VALID_TRACEPARENT = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
MALFORMED_TRACEPARENTS = [
    "garbage",
    "00-xyz-bad-01",
    "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7",  # missing flags
    "00-00000000000000000000000000000000-00f067aa0ba902b7-01",  # all-zero trace id
    "00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01",  # all-zero span id
    "ff-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",  # forbidden version
    "00-4BF92F3577B34DA6A3CE929D0E0E4736-00F067AA0BA902B7-01",  # upper case
    "00-" + "a" * 4000 + "-00f067aa0ba902b7-01",  # oversized
]


def server_spans(spans: list[Any]) -> list[Any]:
    return [s for s in spans if s.kind == SpanKind.SERVER]


def by_trace(spans: list[Any]) -> dict[int, list[Any]]:
    traces: dict[int, list[Any]] = defaultdict(list)
    for span in spans:
        traces[span.context.trace_id].append(span)
    return traces


def trace_id_hex(span: Any) -> str:
    return format(span.context.trace_id, "032x")
