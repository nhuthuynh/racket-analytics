"""Binds the ST-075c rules of tests/features/slo_alerts.feature (NFR-041.3-.5, NFR-042.3-.4).

"is firing" / "is not firing" = the real ``promtool test rules`` (pinned image) on the committed
infra/observability/alerts/slo.yml and a synthetic burn (``slo_rule_fixtures``). The drill
scenarios run scripts/ops/inject_5xx.py against loopback stubs (``fault_drill_stubs``). The
fault seam rule of the same feature is bound in backend/tests/features/test_slo_alerts.py.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from billing_alert_fixtures import needs_docker
from fault_drill_stubs import Stub, run_drill, stub_server
from pytest_bdd import given, parsers, scenario, then, when
from slo_rule_fixtures import ALERTS, SLO_RULES, burn_case, rule_test_doc, run_rule_test

FEATURE = "slo_alerts.feature"
pytestmark = [pytest.mark.scenario]


@pytest.mark.integration
@needs_docker
@scenario(FEATURE, "A burn under the threshold does not fire its alert")
def test_a_burn_under_the_threshold_does_not_fire() -> None:
    pass


@pytest.mark.integration
@needs_docker
@scenario(FEATURE, "A burn over the threshold fires its alert")
def test_a_burn_over_the_threshold_fires() -> None:
    pass


@pytest.mark.integration
@needs_docker
@scenario(FEATURE, "A fast-burn threshold planted at 100 % fails the committed rule test")
def test_a_planted_100_percent_threshold_fails() -> None:
    pass


@pytest.mark.unit
@scenario(FEATURE, "The drill sends the fault header on the requested share of requests")
def test_the_drill_sends_the_header_on_its_share() -> None:
    pass


@pytest.mark.unit
@scenario(FEATURE, "The drill fails when the expected alert never fires")
def test_the_drill_fails_when_the_alert_never_fires() -> None:
    pass


@pytest.mark.unit
@scenario(FEATURE, "A 500 fails a run that expects none")
def test_a_500_fails_a_run_that_expects_none() -> None:
    pass


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    return {"tmp": tmp_path, "rules_text": None}


# ------------------------------------------------- burn-rate rules (promtool)


@given("the SLO rules")
def slo_rules(ctx: dict[str, Any]) -> None:
    assert SLO_RULES.is_file(), f"{SLO_RULES} is missing"


@given(parsers.parse('the SLO rules with the "{alert}" threshold planted at 100 %'))
def planted_rules(ctx: dict[str, Any], alert: str) -> None:
    doc = yaml.safe_load(SLO_RULES.read_text(encoding="utf-8"))
    threshold = f"> {ALERTS[alert].error_ratio:g}"
    for rule in (r for g in doc["groups"] for r in g["rules"] if r.get("alert") == alert):
        assert threshold in rule["expr"], rule["expr"]
        rule["expr"] = rule["expr"].replace(threshold, "> 1")
    ctx["rules_text"] = yaml.safe_dump(doc, sort_keys=False)


@when(parsers.parse("{percent:g} % of {sli} fail for {duration}"))
def burn(ctx: dict[str, Any], percent: float, sli: str, duration: str) -> None:
    ctx["burn"] = (sli, percent, duration)


@when("the committed rule test runs")
def committed_test(ctx: dict[str, Any]) -> None:
    ctx["result"] = run_rule_test(ctx["tmp"], None, ctx["rules_text"])


def _alert_state(ctx: dict[str, Any], alert: str, firing: bool) -> None:
    sli, percent, duration = ctx["burn"]
    assert ALERTS[alert].sli == sli, (alert, sli)
    result = run_rule_test(ctx["tmp"], rule_test_doc(burn_case(alert, percent, duration, firing)))
    assert result.returncode == 0, result.stdout + result.stderr


@then(parsers.parse('"{alert}" is not firing'))
def not_firing(ctx: dict[str, Any], alert: str) -> None:
    _alert_state(ctx, alert, firing=False)


@then(parsers.parse('"{alert}" is firing'))
def firing(ctx: dict[str, Any], alert: str) -> None:
    _alert_state(ctx, alert, firing=True)


@then(parsers.parse('it fails naming "{name}"'))
def fails_naming(ctx: dict[str, Any], name: str) -> None:
    result: subprocess.CompletedProcess[str] = ctx.get("result") or ctx["drill"]
    out = result.stdout + result.stderr
    assert result.returncode != 0, out
    assert name in out, out


# ------------------------------------------------- the drill (inject_5xx.py)


@pytest.fixture
def stub() -> Any:
    with stub_server(Stub()) as s:
        yield s


@given('an API stub that answers 500 to "X-Racket-Fault: 5xx"')
def api_stub(ctx: dict[str, Any], stub: Stub) -> None:
    ctx["stub"] = stub


@given("a Prometheus stub with no firing alert")
def prom_stub(stub: Stub) -> None:
    stub.firing.clear()


def _drill(ctx: dict[str, Any], *args: str) -> None:
    report = ctx["tmp"] / "drill.json"
    ctx["report_path"] = report
    ctx["drill"] = run_drill("--base-url", ctx["stub"].url, "--rps", "200", *args, report=report)


@when(parsers.parse("inject_5xx.py sends {n:d} requests at rate {rate:d}"))
def sends(ctx: dict[str, Any], n: int, rate: int) -> None:
    _drill(ctx, "--requests", str(n), "--rate", str(rate))
    assert ctx["drill"].returncode == 0, ctx["drill"].stdout + ctx["drill"].stderr


@when(parsers.parse('inject_5xx.py runs expecting the alert "{alert}"'))
def expecting_alert(ctx: dict[str, Any], alert: str) -> None:
    stub: Stub = ctx["stub"]
    _drill(ctx, "--requests", "20", "--rate", "10", "--expect-alert", alert,
           "--prom", stub.url, "--poll-s", "0.05")  # fmt: skip


@when(parsers.parse("inject_5xx.py runs at rate {rate:d} expecting no 5xx"))
def expecting_no_5xx(ctx: dict[str, Any], rate: int) -> None:
    _drill(ctx, "--requests", "10", "--rate", str(rate), "--expect-no-5xx")


@then(parsers.parse("{n:d} requests carried the fault header"))
def carried(ctx: dict[str, Any], n: int) -> None:
    assert ctx["stub"].faulted == n


@then(parsers.parse("the report counts {n:d} responses with status 500"))
def report_counts(ctx: dict[str, Any], n: int) -> None:
    report = json.loads(ctx["report_path"].read_text())
    assert report["status_counts"].get("500", 0) == n, report


@then(parsers.parse('it exits 1 naming "{name}"'))
def exits_1(ctx: dict[str, Any], name: str) -> None:
    result = ctx["drill"]
    assert result.returncode == 1, result.stdout + result.stderr
    assert name in result.stdout + result.stderr
