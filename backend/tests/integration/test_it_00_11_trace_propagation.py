"""IT-00-11 (API -> queue -> worker, ST-005 + ST-007): one trace ID appears on the API span,
the enqueue span and the worker span; the trace context travels with the job (AQS/OPS-06)."""

from __future__ import annotations

from typing import Any

import pytest
from opentelemetry.trace import SpanKind

from tests.support import contract
from tests.support.api import ApiDriver
from tests.support.flows import create_match, upload_fixture
from tests.support.tracing import by_trace

pytestmark = [pytest.mark.red_until(story="ST-007"), pytest.mark.slow]


def test_one_trace_from_final_patch_to_probe(api: ApiDriver, span_exporter: Any) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "IT-00-11"))
    api.run(upload_fixture(ivy, match_id))
    span_exporter_spans_before_worker = list(span_exporter.get_finished_spans())

    assert contract.WORKER_RUN_UNTIL_IDLE.load()() >= 1

    spans = list(span_exporter.get_finished_spans())
    enqueue = [s for s in span_exporter_spans_before_worker if "enqueue" in s.name.lower()]
    assert len(enqueue) == 1, [s.name for s in spans]
    trace = by_trace(spans)[enqueue[0].context.trace_id]
    kinds = {s.kind for s in trace}
    names = [s.name.lower() for s in trace]
    assert SpanKind.SERVER in kinds, "the API request span is not in the enqueue's trace"
    assert any(contract.PROBE_STAGE_NAME in n for n in names), "the worker span is in another trace"
    worker = next(s for s in trace if contract.PROBE_STAGE_NAME in s.name.lower())
    assert worker.kind in (SpanKind.CONSUMER, SpanKind.INTERNAL)
    assert worker.parent is not None
