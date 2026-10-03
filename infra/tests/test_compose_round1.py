"""Review round 1 (R1-02/QA-R1-01, QA-R1-02, R1-06): the Compose stack must work on a fresh
volume and behind the web's ``/api`` rewrite.

* tus creation returns ``Location: {API_PUBLIC_PATH_PREFIX}/uploads/{id}``; behind the web
  rewrite the prefix must be ``/api`` or the browser PATCHes a URL Next.js does not route.
* The worker must not race the API's startup migration: a one-shot ``migrate`` service runs
  first, and the worker restarts after a crash.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from test_compose import COMPOSE, ENV_EXAMPLE, compose_config, needs_docker


def raw() -> dict:
    return yaml.safe_load(COMPOSE.read_text())


def env_example() -> dict[str, str]:
    lines = ENV_EXAMPLE.read_text().splitlines()
    return dict(ln.split("=", 1) for ln in lines if ln and ln[0] != "#")


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
@needs_docker
def test_compose_refuses_to_start_without_the_public_path_prefix(tmp_path: Path) -> None:
    lines = [
        ln
        for ln in ENV_EXAMPLE.read_text().splitlines()
        if not ln.startswith("API_PUBLIC_PATH_PREFIX=")
    ]
    env_file = tmp_path / "partial.env"
    env_file.write_text("\n".join(lines) + "\n")

    res = compose_config(env_file)

    assert res.returncode != 0
    assert "API_PUBLIC_PATH_PREFIX" in res.stderr


@pytest.mark.unit
def test_app_services_do_not_start_before_the_schema_is_migrated() -> None:
    svcs = raw()["services"]
    for app in ("api", "worker"):
        assert svcs[app]["depends_on"]["migrate"]["condition"] == (
            "service_completed_successfully"
        ), app


@pytest.mark.unit
def test_the_worker_comes_back_after_a_crash() -> None:
    assert raw()["services"]["worker"].get("restart") in {"unless-stopped", "on-failure", "always"}


# ---------------------------------------------------------------- positive cases
@pytest.mark.unit
def test_env_example_sets_the_api_prefix_used_by_the_web_rewrite() -> None:
    assert env_example()["API_PUBLIC_PATH_PREFIX"] == "/api"


@pytest.mark.unit
@needs_docker
def test_the_api_gets_the_public_path_prefix_from_the_example_env() -> None:
    res = compose_config(ENV_EXAMPLE)

    assert res.returncode == 0, res.stderr
    api_env = yaml.safe_load(res.stdout)["services"]["api"]["environment"]
    assert api_env["API_PUBLIC_PATH_PREFIX"] == "/api"


@pytest.mark.unit
def test_migrate_is_a_one_shot_that_waits_for_postgres() -> None:
    migrate = raw()["services"]["migrate"]

    assert migrate["command"] == ["python", "-m", "racket.platform.migrate"]
    assert migrate["restart"] == "no"
    assert migrate["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert migrate["environment"]["DATABASE_URL"].startswith("postgresql://")
