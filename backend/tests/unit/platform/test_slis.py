"""Service-level indicators (ST-024; NFR-041, NFR-042; AQS/OPS-07; api-sprint-01 §10).

NFR-041 availability = non-5xx / all responses, 429 excluded from both.
NFR-042 upload completion = completed / (created - rejected - cancelled).
Instruments: `http.server.request.duration` (standard) and `racket.upload.sessions` (`event`).
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from racket.platform.slis import (
    HTTP_DURATION_INSTRUMENT,
    UPLOAD_SESSIONS_INSTRUMENT,
    HttpMetricsMiddleware,
    SLIRecorder,
    UploadEvent,
    availability,
    upload_completion,
)


# ---------------------------------------------------------------- negative cases first
@pytest.mark.parametrize("status", [99, 600, -1, 0])
def test_a_status_that_is_not_http_is_refused(status: int) -> None:
    with pytest.raises(ValueError, match="HTTP status"):
        availability([200, status])


def test_availability_of_nothing_is_unknown_not_100_percent() -> None:
    assert availability([]) is None
    assert availability([429, 429]) is None


@pytest.mark.parametrize("status", [500, 502, 503, 504, 599])
def test_server_errors_count_against_availability(status: int) -> None:
    assert availability([200, status]) == 0.5


@pytest.mark.parametrize("status", [201, 204, 301, 400, 401, 403, 404, 409, 413, 422])
def test_client_errors_and_redirects_are_available(status: int) -> None:
    assert availability([status]) == 1.0


def test_rate_limited_requests_do_not_count_against_availability() -> None:
    assert availability([429] * 2 + [200] * 98) == 1.0


def test_an_unknown_upload_event_is_refused() -> None:
    with pytest.raises(ValueError, match="upload event"):
        upload_completion([("created", "teleported")])


def test_an_upload_abandoned_by_the_user_is_not_in_the_base() -> None:
    assert upload_completion([("created", "cancelled")]) == (0, 0)


def test_a_rejected_upload_is_not_in_the_base() -> None:
    assert upload_completion([("created", "rejected")]) == (0, 0)


def test_an_upload_that_expired_counts_against_completion() -> None:
    assert upload_completion([("created", "expired")]) == (0, 1)
    assert upload_completion([("created",)]) == (0, 1)  # still open at read time


def test_a_completed_upload_is_good_resumed_or_not() -> None:
    assert upload_completion([("created", "completed")]) == (1, 1)
    assert upload_completion([("created", "completed"), ("created", "rejected")]) == (1, 1)


# ---------------------------------------------------------------- OpenTelemetry emission
def _points(reader: InMemoryMetricReader, name: str) -> dict[tuple[tuple[str, Any], ...], int]:
    data = reader.get_metrics_data()
    out: dict[tuple[tuple[str, Any], ...], int] = {}
    if data is None:
        return out
    for rm in data.resource_metrics:
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                if metric.name != name:
                    continue
                for p in metric.data.data_points:
                    value = getattr(p, "count", None)
                    out[tuple(sorted(p.attributes.items()))] = int(
                        value if value is not None else p.value
                    )
    return out


@pytest.fixture
def reader() -> InMemoryMetricReader:
    return InMemoryMetricReader()


@pytest.fixture
def recorder(reader: InMemoryMetricReader) -> SLIRecorder:
    return SLIRecorder(MeterProvider(metric_readers=[reader]))


def test_upload_events_are_counted_with_only_event_and_reason(
    recorder: SLIRecorder, reader: InMemoryMetricReader
) -> None:
    recorder.upload_event(UploadEvent.CREATED)
    recorder.upload_event(UploadEvent.CREATED)
    recorder.upload_event(UploadEvent.COMPLETED)
    recorder.upload_event(UploadEvent.REJECTED, reason="not_a_video")
    assert _points(reader, UPLOAD_SESSIONS_INSTRUMENT) == {
        (("event", "created"),): 2,
        (("event", "completed"),): 1,
        (("event", "rejected"), ("reason", "not_a_video")): 1,
    }


def test_a_reason_is_only_allowed_on_rejections(recorder: SLIRecorder) -> None:
    with pytest.raises(ValueError, match="reason"):
        recorder.upload_event(UploadEvent.COMPLETED, reason="x")


async def test_middleware_records_every_response_status(
    recorder: SLIRecorder, reader: InMemoryMetricReader
) -> None:
    async def app(scope: Any, receive: Any, send: Any) -> None:
        status = int(scope["path"].strip("/"))
        await send({"type": "http.response.start", "status": status, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    transport = httpx.ASGITransport(app=HttpMetricsMiddleware(app, recorder=recorder))
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        for status in (200, 429, 500):
            await client.get(f"/{status}?email=a@b.c")
    assert _points(reader, HTTP_DURATION_INSTRUMENT) == {
        (("http.request.method", "GET"), ("http.response.status_code", 200)): 1,
        (("http.request.method", "GET"), ("http.response.status_code", 429)): 1,
        (("http.request.method", "GET"), ("http.response.status_code", 500)): 1,
    }


async def test_an_app_crash_before_any_response_is_recorded_as_500(
    recorder: SLIRecorder, reader: InMemoryMetricReader
) -> None:
    async def app(scope: Any, receive: Any, send: Any) -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await HttpMetricsMiddleware(app, recorder=recorder)(
            {"type": "http", "method": "POST", "path": "/"}, None, None
        )
    assert _points(reader, HTTP_DURATION_INSTRUMENT) == {
        (("http.request.method", "POST"), ("http.response.status_code", 500)): 1,
    }


async def test_an_unusual_method_is_bucketed_to_limit_cardinality(
    recorder: SLIRecorder, reader: InMemoryMetricReader
) -> None:
    async def app(scope: Any, receive: Any, send: Any) -> None:
        await send({"type": "http.response.start", "status": 405, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    await HttpMetricsMiddleware(app, recorder=recorder)(
        {"type": "http", "method": "XYZZY", "path": "/"}, None, _noop_send
    )
    assert _points(reader, HTTP_DURATION_INSTRUMENT) == {
        (("http.request.method", "_OTHER"), ("http.response.status_code", 405)): 1,
    }


async def _noop_send(message: Any) -> None:
    return None
