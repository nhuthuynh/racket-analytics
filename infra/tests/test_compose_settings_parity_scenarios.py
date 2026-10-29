"""Binds tests/features/compose_settings_parity.feature (SRE-VERIFY04R3-02). Negative case first.

The parity check runs on the real infra/env.example, infra/compose.yaml and backend Settings, or on
copies with one planted setting (retro C3: the check must fail on a planted unforwarded setting).
"The stack configuration" is the real ``docker compose config`` of infra/compose.yaml.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from compose_env_parity import check
from conftest import REPO_ROOT
from pytest_bdd import given, parsers, scenarios, then, when
from test_compose import COMPOSE, ENV_EXAMPLE, compose_config

SETTINGS_PY = REPO_ROOT / "backend" / "src" / "racket" / "platform" / "settings.py"
needs_docker = pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI missing")

pytestmark = [pytest.mark.scenario, pytest.mark.integration]
scenarios("compose_settings_parity.feature")


def names(csv: str) -> list[str]:
    return [n.strip() for n in csv.split(",")]


@given(
    parsers.parse('env.example declares "{name}" which the backend Settings reads'),
    target_fixture="ctx",
)
def planted(tmp_path: Path, name: str) -> dict:
    env, settings = tmp_path / "env.example", tmp_path / "settings.py"
    env.write_text(ENV_EXAMPLE.read_text() + f"{name}=false\n")
    settings.write_text(SETTINGS_PY.read_text() + f'\nPLANTED = boolean("{name}", default=False)\n')
    return {"env": env, "compose": tmp_path / "compose.yaml", "settings": settings}


@given("compose.yaml does not forward it")
def compose_unchanged(ctx: dict) -> None:
    ctx["compose"].write_text(COMPOSE.read_text())


@given("the shipped env.example and compose.yaml", target_fixture="ctx")
def shipped() -> dict:
    return {"env": ENV_EXAMPLE, "compose": COMPOSE, "settings": SETTINGS_PY}


@given("an env file copied from env.example", target_fixture="ctx")
def env_copy(tmp_path: Path) -> dict:
    env = tmp_path / "stack.env"
    env.write_text(ENV_EXAMPLE.read_text())
    return {"env": env}


@given(parsers.parse('the env file sets "{settings}" to "{value}"'))
def env_sets(ctx: dict, settings: str, value: str) -> None:
    wanted = names(settings)
    kept = [ln for ln in ctx["env"].read_text().splitlines() if ln.split("=", 1)[0] not in wanted]
    ctx["env"].write_text("\n".join([*kept, *(f"{n}={value}" for n in wanted)]) + "\n")


@when("the env-to-Compose parity check runs")
def run_check(ctx: dict) -> None:
    ctx["problems"] = check(ctx["env"], ctx["compose"], ctx["settings"])


@when("Compose renders the stack configuration")
def render(ctx: dict) -> None:
    if shutil.which("docker") is None:
        pytest.skip("docker CLI missing")
    res = compose_config(ctx["env"])
    assert res.returncode == 0, res.stderr
    ctx["services"] = yaml.safe_load(res.stdout)["services"]


@then(parsers.parse('it fails naming "{name}" for the services "{services}"'))
def fails_naming(ctx: dict, name: str, services: str) -> None:
    problems = ctx["problems"]
    assert any(p.startswith(f"{name}: in env.example but not forwarded") for p in problems)
    for service in names(services):
        assert f"{name}: read by Settings but not forwarded to {service}" in problems, problems


@then("it reports no problem")
def no_problem(ctx: dict) -> None:
    assert ctx["problems"] == []


@then(parsers.parse('"{settings}" are "{value}" in "{services}"'))
@then(parsers.parse('"{settings}" is "{value}" in "{services}"'))
def rendered_values(ctx: dict, settings: str, value: str, services: str) -> None:
    for service in names(services):
        env = ctx["services"][service]["environment"]
        for name in names(settings):
            assert env.get(name) == value, (service, name, env.get(name))
