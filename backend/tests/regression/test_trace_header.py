"""Mandatory regression suite: trace header (IT-00-12; testing-strategy §5; NFR-076;
AQS/OPS-06 W3C Trace Context). Never deleted."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.support.tracing import (
    MALFORMED_TRACEPARENTS,
    VALID_TRACEPARENT,
    server_spans,
    trace_id_hex,
)


@pytest.mark.parametrize("traceparent", MALFORMED_TRACEPARENTS, ids=lambda v: v[:40])
async def test_malformed_traceparent_still_succeeds_under_a_new_trace(
    api_client: httpx.AsyncClient, span_exporter: Any, traceparent: str
) -> None:
    response = await api_client.get("/healthz", headers={"traceparent": traceparent})

    assert 200 <= response.status_code < 300
    spans = server_spans(list(span_exporter.get_finished_spans()))
    assert spans, "no server span recorded"
    for span in spans:
        assert span.context.trace_id != 0
        assert span.parent is None or not span.parent.is_remote
        assert trace_id_hex(span) not in traceparent.lower()


async def test_valid_traceparent_is_continued(
    api_client: httpx.AsyncClient, span_exporter: Any
) -> None:
    """Positive control: without it, ignoring the header entirely would pass the suite."""
    response = await api_client.get("/healthz", headers={"traceparent": VALID_TRACEPARENT})

    assert 200 <= response.status_code < 300
    spans = server_spans(list(span_exporter.get_finished_spans()))
    assert spans
    assert {trace_id_hex(s) for s in spans} == {VALID_TRACEPARENT.split("-")[1]}


async def test_tracestate_garbage_is_ignored(
    api_client: httpx.AsyncClient, span_exporter: Any
) -> None:
    response = await api_client.get(
        "/healthz", headers={"traceparent": VALID_TRACEPARENT, "tracestate": "=,,=\x7f" * 100}
    )

    assert 200 <= response.status_code < 300
