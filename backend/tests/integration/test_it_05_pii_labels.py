"""IT-05-01 (ST-075a; NFR-069.1; threat notes T5-OB-1, T5-OB-2; AQS/SEC-04 16.2.5, AQS/OPS-07).

1. Export: the API and the worker post their SLI metrics over OTLP/HTTP to the endpoint in
   ``OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`` (a real receiver on 127.0.0.1 that decodes the
   protobuf, standing in for the ST-075b collector).
2. PII scan: after a demo run (match, upload, worker, a cross-user read) every metric
   attribute and every log line is scanned for emails, nicknames and signed URLs: 0 found.
3. Negative: an email planted in a metric attribute is found by the scan, and an email planted
   in the one free-text attribute (the upload rejection ``reason``) never reaches the TSDB.
"""

from __future__ import annotations

import json
import logging

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from racket.platform.slis import UPLOAD_SESSIONS_INSTRUMENT, SLIRecorder, UploadEvent
from tests.support import contract
from tests.support.api import ApiDriver
from tests.support.flows import create_match, upload_fixture
from tests.support.logscan import scan
from tests.support.telemetry import (
    API_SCRIPT,
    WORKER_SCRIPT,
    global_metric_reader,
    metric_lines,
    otlp_receiver,
    run_service,
)

pytestmark = pytest.mark.slow

NICKNAMES = ["ivy", "carlos"]
PLANTED_EMAIL = "ivy.player@example.com"


def _demo_run(api: ApiDriver) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "Telemetry scan with Carlos"))
    api.run(upload_fixture(ivy, match_id))
    contract.WORKER_RUN_UNTIL_IDLE.load()()
    api.request("carlos", "GET", contract.MATCH.format(match_id=match_id))  # a 404 (BOLA)


# ---------------------------------------------------------------- negative cases first
def test_an_email_planted_in_a_metric_attribute_is_found() -> None:
    reader = InMemoryMetricReader()
    meter = MeterProvider(metric_readers=[reader]).get_meter("planted")
    meter.create_counter("planted.counter").add(1, {"player": PLANTED_EMAIL})

    leaks = scan(metric_lines(reader.get_metrics_data()), nicknames=NICKNAMES)

    assert {leak.kind for leak in leaks} == {"email", "nickname"}


def test_an_email_planted_in_the_rejection_reason_never_reaches_an_attribute() -> None:
    reader = global_metric_reader()

    SLIRecorder().upload_event(UploadEvent.REJECTED, reason=PLANTED_EMAIL)

    lines = [
        line for line in metric_lines(reader.get_metrics_data())
        if line.startswith(UPLOAD_SESSIONS_INSTRUMENT)
    ]  # fmt: skip
    assert lines, "no upload data point was collected; the scan would be vacuous"
    assert scan(lines, nicknames=NICKNAMES) == []


# ---------------------------------------------------------------- export over OTLP
def test_the_api_and_the_worker_export_metrics_when_the_endpoint_is_set() -> None:
    with otlp_receiver() as (endpoint, received):
        api = run_service(API_SCRIPT, endpoint)
        worker = run_service(WORKER_SCRIPT, endpoint)

    assert api.returncode == 0, api.stderr[-2000:]
    assert worker.returncode == 0, worker.stderr[-2000:]
    assert set(received.paths) == {"/v1/metrics"}
    assert {"racket-api", "racket-worker"} <= received.services
    assert "http.server.request.duration" in received.instruments["racket-api"]
    assert UPLOAD_SESSIONS_INSTRUMENT in received.instruments["racket-worker"]
    assert scan(received.lines, nicknames=NICKNAMES) == []


# ---------------------------------------------------------------- the demo run scan
def test_no_personal_data_in_metric_attributes_or_logs_after_a_demo_run(
    api: ApiDriver, caplog: pytest.LogCaptureFixture, capfd: pytest.CaptureFixture[str]
) -> None:
    reader = global_metric_reader()
    with caplog.at_level(logging.DEBUG):
        _demo_run(api)
    out, err = capfd.readouterr()
    logs = out.splitlines() + err.splitlines() + [caplog.handler.format(r) for r in caplog.records]
    logs += [json.dumps(r.__dict__, default=str) for r in caplog.records]
    attributes = metric_lines(reader.get_metrics_data())

    assert logs, "nothing was logged; the log scan would be vacuous"
    assert any(line.startswith("http.server.request.duration") for line in attributes)
    assert any(line.startswith(UPLOAD_SESSIONS_INSTRUMENT) for line in attributes)
    assert scan(attributes, nicknames=NICKNAMES) == []
    assert scan(logs, nicknames=NICKNAMES) == []
