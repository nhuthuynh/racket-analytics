"""Binds tests/features/billing_alerts.feature (ST-073, NFR-022). Negative case first.

"An alert fires" = the real ``promtool test rules`` (pinned image) evaluating the committed
infra/observability/alerts/billing.yml against a budget metric and a month-to-date spend series
and agreeing with the expected alert set; see ``billing_alert_fixtures``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from billing_alert_fixtures import (
    BUDGET_METRIC,
    THRESHOLDS,
    full_env,
    needs_docker,
    render_budgets,
    rule_test_doc,
    run_rule_test,
)
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration, needs_docker]
scenarios("billing_alerts.feature")


def _assert_promtool_ok(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SUCCESS" in result.stdout + result.stderr


@given(parsers.parse('the monthly budget for "{provider}" is {budget:d} USD'), target_fixture="ctx")
def budget(provider: str, budget: int, tmp_path: Path) -> dict:
    return {"provider": provider, "budget": budget, "tmp": tmp_path}


@when(parsers.parse('the month-to-date spend for "{provider}" is {percent:d}% of the budget'))
def spend(ctx: dict, provider: str, percent: int) -> None:
    assert provider == ctx["provider"]
    ctx["percent"] = percent


@then(parsers.parse('no billing alert fires for "{provider}"'))
def no_alert(ctx: dict, provider: str) -> None:
    doc = rule_test_doc(provider, ctx["percent"], ctx["budget"], dict.fromkeys(THRESHOLDS, False))
    _assert_promtool_ok(run_rule_test(ctx["tmp"], doc))


@then(parsers.parse('the {threshold:d}% alert for "{provider}" does not fire'))
def alert_silent(ctx: dict, threshold: int, provider: str) -> None:
    doc = rule_test_doc(provider, ctx["percent"], ctx["budget"], {threshold: False})
    _assert_promtool_ok(run_rule_test(ctx["tmp"], doc))


@then(parsers.parse('the {threshold:d}% alert for "{provider}" fires'))
def alert_fires(ctx: dict, threshold: int, provider: str) -> None:
    doc = rule_test_doc(provider, ctx["percent"], ctx["budget"], {threshold: True})
    _assert_promtool_ok(run_rule_test(ctx["tmp"], doc))


# ------------------------------------------------------------------ budgets from env settings


@given(
    parsers.parse('every billing setting is set except "{name}"'),
    target_fixture="settings",
)
def settings_missing(name: str, tmp_path: Path) -> dict:
    env = full_env(tmp_path)
    del env[name]
    return {"env": env}


@given("every billing setting is set", target_fixture="settings")
def settings_full(tmp_path: Path) -> dict:
    return {"env": full_env(tmp_path)}


@when("the budget metrics are rendered")
def rendered(settings: dict) -> None:
    settings["result"] = render_budgets(settings["env"])


@then(parsers.parse('rendering fails naming "{name}"'))
def fails_naming(settings: dict, name: str) -> None:
    result = settings["result"]
    assert result.returncode != 0
    assert name in result.stderr


@then("no budget metric is written")
def nothing_written(settings: dict) -> None:
    assert BUDGET_METRIC not in settings["result"].stdout


@then(parsers.parse('a budget metric is written for "{first}" and "{second}"'))
def written(settings: dict, first: str, second: str) -> None:
    result = settings["result"]
    assert result.returncode == 0, result.stderr
    for provider in (first, second):
        assert f'{BUDGET_METRIC}{{provider="{provider}"}}' in result.stdout
