"""IT-05-12 (ST-075d; NFR-041.5 fault path, NFR-041.6; threat note T5-OB-5; PE-PLAN05-R2-03).

The whole API from ``create_app`` over ``ASGITransport``, with ``Settings`` read by
``Settings.from_env`` and the session's OTel ``InMemoryMetricReader`` on the global meter
provider: ``X-Racket-Fault: 5xx`` gives a 500 only when ``APP_ENV=test`` and the seam value is
``api:5xx_on_header``, and that 500 is recorded in ``http.server.request.duration`` with
``http.response.status_code=500`` (the fault middleware sits inside ``HttpMetricsMiddleware``).
"""

from __future__ import annotations

import os

import httpx
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from racket.platform.app import create_app
from racket.platform.settings import Settings
from racket.platform.slis import HTTP_DURATION_INSTRUMENT, METER_NAME
from tests.support.api import async_client
from tests.support.errors import assert_generic_error
from tests.support.telemetry import global_metric_reader

SEAM = "api:5xx_on_header"
FAULT_HEADER = {"X-Racket-Fault": "5xx"}


def _settings(app_env: str) -> Settings:
    return Settings.from_env({**os.environ, "APP_ENV": app_env, "RACKET_FAULT_INJECTION": SEAM})


def _count(reader: InMemoryMetricReader, status: int) -> int:
    """Cumulative count of ``GET`` responses with ``status`` in the racket request duration
    histogram (the FastAPI instrumentation's own histogram of the same name is not the SLI)."""
    data = reader.get_metrics_data()
    total = 0
    for rm in data.resource_metrics if data else ():
        for sm in rm.scope_metrics:
            if sm.scope.name != METER_NAME:
                continue
            for metric in sm.metrics:
                if metric.name != HTTP_DURATION_INSTRUMENT:
                    continue
                for point in metric.data.data_points:
                    attrs = point.attributes
                    if attrs.get("http.response.status_code") == status and (
                        attrs.get("http.request.method") == "GET"
                    ):
                        total += point.count
    return total


async def _get(app_env: str, headers: dict[str, str]) -> httpx.Response:
    async with async_client(create_app(_settings(app_env))) as client:
        return await client.get("/healthz", headers=headers)


# ---------------------------------------------------------------- negative cases first
async def test_the_header_under_app_env_dev_is_not_a_500_and_not_recorded_as_one() -> None:
    reader = global_metric_reader()
    before = _count(reader, 500)

    response = await _get("dev", FAULT_HEADER)

    assert response.status_code == 200
    assert _count(reader, 500) == before


async def test_the_seam_without_the_header_answers_normally() -> None:
    assert (await _get("test", {})).status_code == 200


# ---------------------------------------------------------------- the fault path
async def test_an_injected_500_is_recorded_in_the_request_duration_histogram() -> None:
    reader = global_metric_reader()
    before = _count(reader, 500)

    response = await _get("test", FAULT_HEADER)

    assert_generic_error(response, 500)
    assert response.headers["x-content-type-options"] == "nosniff"  # inside EdgeMiddleware
    assert response.headers["x-request-id"]
    assert _count(reader, 500) == before + 1
