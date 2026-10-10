"""Binds tests/features/purge_compose_service.feature (SRE-PURGE-b; NFR-066 c, NFR-054; ADR 0038).

Renders ``infra/compose.yaml`` with the real ``docker compose config`` and an env file copied
from ``infra/env.example`` (the operator path), then checks the rendered ``purge`` service:
the identity it holds, its network and the schedule it gets. The live run on a full stack is
recorded in ``docs/ops/purge-schedule.md`` (it needs the API image built, which the infra job's
budget does not hold). Negative case first in the feature.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when
from test_compose import ENV_EXAMPLE, compose_config

pytestmark = [pytest.mark.scenario, pytest.mark.integration]
scenarios("purge_compose_service.feature")

SCHEDULER_IN_IMAGE = "/opt/racket/purge_schedule.py"


def _env_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


@pytest.fixture
def world(tmp_path: Path) -> dict[str, Any]:
    if shutil.which("docker") is None:
        pytest.skip("docker CLI missing (the infra CI job runs this on ubuntu-24.04)")
    return {"tmp": tmp_path}


def _purge(world: dict[str, Any]) -> dict[str, Any]:
    res = world["rendered"]
    assert res.returncode == 0, res.stderr
    svc = yaml.safe_load(res.stdout)["services"].get("purge")
    assert svc is not None, "no `purge` service in the rendered Compose configuration (ADR 0038)"
    return svc


# ---------------------------------------------------------------- given
@given("the stack environment from infra/env.example")
def stack_env(world: dict[str, Any]) -> None:
    world["env_text"] = ENV_EXAMPLE.read_text()


@given("PURGE_INTERVAL_S is not set")
def interval_unset(world: dict[str, Any]) -> None:
    assert "PURGE_INTERVAL_S" not in _env_values(world["env_text"])


@given(parsers.parse('PURGE_INTERVAL_S is set to "{seconds}"'))
def interval_set(world: dict[str, Any], seconds: str) -> None:
    world["env_text"] += f"\nPURGE_INTERVAL_S={seconds}\n"


# ---------------------------------------------------------------- when
@when("the Compose configuration is rendered")
def render(world: dict[str, Any]) -> None:
    env_file = world["tmp"] / ".env"
    env_file.write_text(world["env_text"])
    world["values"] = _env_values(world["env_text"])
    world["rendered"] = compose_config(env_file)


# ---------------------------------------------------------------- then
@then(
    parsers.parse(
        'the purge service connects to the database as "{app_var}", not as "{worker_var}"'
    )
)
def database_login(world: dict[str, Any], app_var: str, worker_var: str) -> None:
    login = urlsplit(_purge(world)["environment"]["DATABASE_URL"]).username
    assert world["values"][app_var] != world["values"][worker_var]
    assert login == world["values"][app_var], login
    assert login != world["values"][worker_var], login


@then(parsers.parse('the purge service uses the object-store key "{app_var}", not "{worker_var}"'))
def store_key(world: dict[str, Any], app_var: str, worker_var: str) -> None:
    env = _purge(world)["environment"]
    assert world["values"][app_var] != world["values"][worker_var]
    assert env["S3_ACCESS_KEY_ID"] == world["values"][app_var]
    assert world["values"][worker_var] not in env.values()
    secret = worker_var.replace("ACCESS_KEY_ID", "SECRET_ACCESS_KEY")
    assert world["values"][secret] not in env.values()


@then(parsers.parse('the purge service is on the "{network}" network only'))
def network_only(world: dict[str, Any], network: str) -> None:
    assert list(_purge(world)["networks"]) == [network]


@then(parsers.parse('the purge service\'s PURGE_INTERVAL_S is "{seconds}"'))
def rendered_interval(world: dict[str, Any], seconds: str) -> None:
    assert str(_purge(world)["environment"]["PURGE_INTERVAL_S"]) == seconds


@then(parsers.parse('the purge service runs "{job}" under the purge scheduler'))
def runs_job(world: dict[str, Any], job: str) -> None:
    assert _purge(world)["command"] == ["python", SCHEDULER_IN_IMAGE, *job.split()]
