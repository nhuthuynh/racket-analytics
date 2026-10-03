"""Steps for tests/features/errors_and_tracing.feature (ST-005, ST-007; NFR-058, NFR-076;
AQS/SEC-04 generic errors, AQS/OPS-06 W3C Trace Context)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from pytest_bdd import given, scenarios, then, when

from tests.support import contract
from tests.support.api import ApiDriver
from tests.support.errors import ExplodingService, assert_generic_error, assert_no_internals
from tests.support.flows import create_match, upload_fixture
from tests.support.tracing import by_trace, server_spans, trace_id_hex

pytestmark = pytest.mark.red_until(story="ST-005")

scenarios("errors_and_tracing.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given("the match service fails unexpectedly")
def service_fails(api: ApiDriver, ctx: dict[str, Any]) -> None:
    ctx["match_id"] = api.run(create_match(api.as_user("ivy"), "Error test"))
    dependency = contract.MATCH_SERVICE_DEPENDENCY.load()
    api.app.dependency_overrides[dependency] = ExplodingService


@when("Ivy opens one of her matches", target_fixture="response")
def open_match(api: ApiDriver, ctx: dict[str, Any]) -> httpx.Response:
    return api.request("ivy", "GET", contract.MATCH.format(match_id=ctx["match_id"]))


@then("she gets a generic error with a support reference")
def generic_error(response: httpx.Response) -> None:
    assert_generic_error(response, 500)


@then("the response contains no stack trace, query or internal identifier")
def no_internals(response: httpx.Response) -> None:
    assert_no_internals(response.text)
    assert_no_internals(str(dict(response.headers)))


@given("tracing is enabled")
def tracing_enabled(span_exporter: Any) -> None:
    assert span_exporter.get_finished_spans() == ()


@when("Ivy completes an upload and the probe job runs")
def upload_and_probe(api: ApiDriver) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "Trace test"))
    api.run(upload_fixture(ivy, match_id))
    assert contract.WORKER_RUN_UNTIL_IDLE.load()() >= 1


@then("the API request, the enqueue and the probe stage share one trace ID")
def one_trace(span_exporter: Any) -> None:
    spans = list(span_exporter.get_finished_spans())
    for trace_spans in by_trace(spans).values():
        names = [s.name.lower() for s in trace_spans]
        if (
            server_spans(trace_spans)
            and any("enqueue" in n for n in names)
            and any(contract.PROBE_STAGE_NAME in n for n in names)
        ):
            return
    pytest.fail(
        f"no single trace holds request, enqueue and probe spans: {[s.name for s in spans]}"
    )


@given('a request carries a malformed "traceparent" header', target_fixture="traceparent")
def malformed_header(span_exporter: Any) -> str:
    return "00-xyz-bad-01"


@when("the request reaches the API", target_fixture="response")
def send_request(api: ApiDriver, traceparent: str) -> httpx.Response:
    return api.request("anonymous", "GET", "/healthz", headers={"traceparent": traceparent})


@then("the request succeeds")
def succeeds(response: httpx.Response) -> None:
    assert 200 <= response.status_code < 300


@then("it is recorded under a new trace")
def new_trace(span_exporter: Any, traceparent: str) -> None:
    spans = server_spans(list(span_exporter.get_finished_spans()))
    assert spans, "no server span recorded"
    for span in spans:
        assert span.parent is None or not span.parent.is_remote
        assert trace_id_hex(span) not in traceparent
        assert span.context.trace_id != 0
