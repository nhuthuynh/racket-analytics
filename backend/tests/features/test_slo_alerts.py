"""Steps for the fault seam rule of tests/features/slo_alerts.feature (ST-075d; NFR-041.6;
ADR 0012). One ``@scenario`` per name: other rules of the feature bind in their own modules."""

from __future__ import annotations

import os
from typing import Any

import httpx
import pytest
from pytest_bdd import given, parsers, scenario, then, when

from racket.platform.app import create_app
from racket.platform.settings import Settings
from racket.platform.slis import HTTP_DURATION_INSTRUMENT, METER_NAME
from tests.support.api import ApiDriver
from tests.support.errors import assert_generic_error
from tests.support.telemetry import global_metric_reader

FEATURE = "slo_alerts.feature"


@scenario(FEATURE, "The fault seam is inert outside the test environment")
def test_the_fault_seam_is_inert_outside_the_test_environment() -> None:
    pass


@scenario(FEATURE, "An injected API fault is a 500 counted against availability")
def test_an_injected_api_fault_is_a_500_counted_against_availability() -> None:
    pass


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


def _server_errors() -> int:
    data = global_metric_reader().get_metrics_data()
    return sum(
        point.count
        for rm in (data.resource_metrics if data else ())
        for sm in rm.scope_metrics
        if sm.scope.name == METER_NAME
        for metric in sm.metrics
        if metric.name == HTTP_DURATION_INSTRUMENT
        for point in metric.data.data_points
        if point.attributes.get("http.response.status_code") == 500
    )


@given(parsers.parse('the API runs with APP_ENV "{app_env}" and the fault seam "{seam}"'))
def api_with_seam(app_env: str, seam: str, ctx: dict[str, Any]) -> None:
    env = {**os.environ, "APP_ENV": app_env, "RACKET_FAULT_INJECTION": seam}
    ctx["errors_before"] = _server_errors()
    ctx["driver"] = ApiDriver(create_app(Settings.from_env(env)))


@when(parsers.parse('a request carries the header "{name}: {value}"'), target_fixture="response")
def request_with_header(name: str, value: str, ctx: dict[str, Any]) -> httpx.Response:
    driver: ApiDriver = ctx["driver"]
    try:
        return driver.request("anonymous", "GET", "/healthz", headers={name: value})
    finally:
        driver.close()


@then("the API answers normally")
def answers_normally(response: httpx.Response) -> None:
    assert response.status_code == 200, response.text[:300]


@then("the API answers with a generic 500 error")
def generic_500(response: httpx.Response) -> None:
    assert_generic_error(response, 500)


@then("the 500 is recorded in the request duration metric")
def recorded(ctx: dict[str, Any]) -> None:
    assert _server_errors() == ctx["errors_before"] + 1
