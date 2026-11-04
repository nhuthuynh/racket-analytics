"""API binding of tests/features/pseudonymous_telemetry.feature (ST-075a; NFR-069.1; T5-OB-1,
T5-OB-2). Same mechanics as IT-05-01: a real OTLP/HTTP receiver, the API and worker entry
points in their own processes, and the NFR-069 scanner over metric attributes and log lines.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from pytest_bdd import given, scenario, then, when

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

FEATURE = "pseudonymous_telemetry.feature"
NICKNAMES = ["ivy", "carlos"]
pytestmark = pytest.mark.slow


@scenario(FEATURE, "The API and the worker export their metrics to the configured collector")
def test_export_to_the_collector() -> None:
    pass


@scenario(FEATURE, "A demo run leaves no personal data in metric attributes or logs")
def test_demo_run_is_pseudonymous() -> None:
    pass


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given("a metrics collector endpoint is configured")
def collector(ctx: dict[str, Any]) -> None:
    ctx["receiver"] = otlp_receiver()
    ctx["endpoint"], ctx["received"] = ctx["receiver"].__enter__()


@when("the API answers a request and the worker refuses an upload")
def run_services(ctx: dict[str, Any]) -> None:
    try:
        ctx["runs"] = [run_service(s, ctx["endpoint"]) for s in (API_SCRIPT, WORKER_SCRIPT)]
    finally:
        ctx["receiver"].__exit__(None, None, None)


@then("the collector receives metrics from the API and from the worker")
def both_exported(ctx: dict[str, Any]) -> None:
    assert [run.returncode for run in ctx["runs"]] == [0, 0], [r.stderr[-800:] for r in ctx["runs"]]
    assert {"racket-api", "racket-worker"} <= ctx["received"].services


@then("no exported attribute holds an email, a nickname or a signed URL")
def exported_clean(ctx: dict[str, Any]) -> None:
    assert ctx["received"].lines
    assert scan(ctx["received"].lines, nicknames=NICKNAMES) == []


@given("Ivy has created a match with Carlos in the title and uploaded its video")
def ivy_uploads(ctx: dict[str, Any], api: ApiDriver) -> None:
    ctx["reader"] = global_metric_reader()
    ivy = api.as_user("ivy")
    ctx["match_id"] = api.run(create_match(ivy, "Scenario with Carlos"))
    api.run(upload_fixture(ivy, ctx["match_id"]))


@when("the worker processes the video and Carlos tries to open Ivy's match")
def worker_and_carlos(
    ctx: dict[str, Any], api: ApiDriver, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        contract.WORKER_RUN_UNTIL_IDLE.load()()
        api.request("carlos", "GET", contract.MATCH.format(match_id=ctx["match_id"]))


@then("no metric attribute or log line holds an email, a nickname or a signed URL")
def nothing_personal(
    ctx: dict[str, Any], caplog: pytest.LogCaptureFixture, capfd: pytest.CaptureFixture[str]
) -> None:
    out, err = capfd.readouterr()
    logs = out.splitlines() + err.splitlines() + [caplog.handler.format(r) for r in caplog.records]
    logs += [json.dumps(r.__dict__, default=str) for r in caplog.records]
    attributes = metric_lines(ctx["reader"].get_metrics_data())
    assert logs and attributes
    assert scan(attributes, nicknames=NICKNAMES) == []
    assert scan(logs, nicknames=NICKNAMES) == []
