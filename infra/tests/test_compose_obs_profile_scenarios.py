"""Binds the static scenarios of tests/features/compose_obs_profile.feature (ST-075b).

"The obs profile check" is ``compose_obs.check`` on the real files or on a copy with one planted
change. "The stack configuration" is the real ``docker compose config`` of infra/compose.yaml.
The two live scenarios are bound in test_compose_obs_live.py (IT-05-02). Negative cases first.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from compose_obs import ALERTS_DIR, COLLECTOR_YML, OBS_OVERLAY, PROMETHEUS_YML, check
from pytest_bdd import given, parsers, scenario, then, when
from test_compose import COMPOSE, ENV_EXAMPLE, compose_config

FEATURE = "compose_obs_profile.feature"
needs_docker = pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI missing")
pytestmark = [pytest.mark.scenario, pytest.mark.integration]


@scenario(FEATURE, "A Prometheus port published on every interface is refused")
def test_public_prometheus_port_refused() -> None:
    pass


@scenario(FEATURE, "A Prometheus rule-file glob is refused")
def test_rule_file_glob_refused() -> None:
    pass


@scenario(FEATURE, "The shipped obs profile passes the check")
def test_shipped_obs_profile_passes() -> None:
    pass


@needs_docker
@scenario(FEATURE, "Without the obs profile the stack and its exports are unchanged")
def test_default_stack_unchanged() -> None:
    pass


@needs_docker
@scenario(FEATURE, "The obs overlay turns on the profile and the metrics export")
def test_obs_overlay_turns_on_export() -> None:
    pass


def names(csv: str) -> list[str]:
    return [n.strip() for n in csv.split(",")]


@given(parsers.parse('a copy of compose.yaml whose prometheus port is "{port}"'), target_fixture="ctx")
def planted_port(tmp_path: Path, port: str) -> dict:
    copy = tmp_path / "compose.yaml"
    copy.write_text(
        COMPOSE.read_text().replace("127.0.0.1:${PROMETHEUS_HOST_PORT:-9090}:9090", port)
    )
    return {"files": (copy, PROMETHEUS_YML, COLLECTOR_YML)}


@given(parsers.parse('a copy of prometheus.yml whose rule_files is "{glob}"'), target_fixture="ctx")
def planted_glob(tmp_path: Path, glob: str) -> dict:
    copy = tmp_path / "prometheus.yml"
    copy.write_text(PROMETHEUS_YML.read_text().replace("/etc/prometheus/rules/billing.yml", glob))
    return {"files": (COMPOSE, copy, COLLECTOR_YML)}


@given("the shipped compose.yaml and obs config files", target_fixture="ctx")
def shipped() -> dict:
    return {"files": (COMPOSE, PROMETHEUS_YML, COLLECTOR_YML)}


@when("the obs profile check runs")
def run_check(ctx: dict) -> None:
    ctx["problems"] = check(*ctx["files"], ALERTS_DIR)


@then(parsers.parse('it fails naming "{first}" and "{second}"'))
def fails_naming_both(ctx: dict, first: str, second: str) -> None:
    assert any(first in p and second in p for p in ctx["problems"]), ctx["problems"]


@then(parsers.re(r'it fails naming "(?P<what>[^"]+)"$'))
def fails_naming(ctx: dict, what: str) -> None:
    assert any(what in p for p in ctx["problems"]), ctx["problems"]


@then("it reports no problem")
def no_problem(ctx: dict) -> None:
    assert ctx["problems"] == []


@given("an env file copied from env.example", target_fixture="ctx")
def env_copy(tmp_path: Path) -> dict:
    env = tmp_path / "env"
    env.write_text(ENV_EXAMPLE.read_text())
    return {"env": env}


@given("the obs overlay appended to it")
def append_overlay(ctx: dict) -> None:
    ctx["env"].write_text(ctx["env"].read_text() + OBS_OVERLAY.read_text())


@when("Compose renders the stack configuration")
def render(ctx: dict) -> None:
    res = compose_config(ctx["env"])
    assert res.returncode == 0, res.stderr
    ctx["config"] = yaml.safe_load(res.stdout)


@then(parsers.parse('"{csv}" are not in the stack'))
def not_in_stack(ctx: dict, csv: str) -> None:
    assert not set(names(csv)) & set(ctx["config"]["services"])


@then(parsers.parse('"{csv}" are in the stack'))
def in_stack(ctx: dict, csv: str) -> None:
    assert set(names(csv)) <= set(ctx["config"]["services"])


@then(parsers.re(r'"(?P<name>[A-Z0-9_]+)" is "(?P<value>[^"]*)" in "(?P<csv>[^"]+)"'))
def env_value(ctx: dict, name: str, value: str, csv: str) -> None:
    for service in names(csv):
        env = ctx["config"]["services"][service].get("environment") or {}
        assert str(env.get(name, "")) == value, (service, name, env.get(name))
