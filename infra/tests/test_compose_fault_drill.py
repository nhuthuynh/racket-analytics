"""The drill-only Compose override (ST-075c; NFR-041.5; ADR 0012; SEC-5 T5-OB-5).

infra/compose.fault-drill.yaml adds exactly one setting, ``RACKET_FAULT_INJECTION:
api:5xx_on_header``, to the ``api`` service. The shipped files never name the seam variable and
``infra/env.example`` keeps ``APP_ENV=dev``, so a ``make up`` stack drops the seam (the API's
``Settings.from_env`` keeps it only under ``APP_ENV=test``). Negative pins first.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml
from billing_alert_fixtures import needs_docker
from test_compose import COMPOSE, ENV_EXAMPLE

OVERRIDE = COMPOSE.parent / "compose.fault-drill.yaml"
SEAM = "RACKET_FAULT_INJECTION"
SEAM_VALUE = "api:5xx_on_header"


@pytest.mark.unit
@pytest.mark.parametrize("shipped", [COMPOSE, ENV_EXAMPLE], ids=lambda p: p.name)
def test_shipped_files_never_name_the_seam_variable(shipped: Path) -> None:
    assert SEAM not in shipped.read_text(encoding="utf-8")


@pytest.mark.unit
def test_env_example_keeps_app_env_dev() -> None:
    lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    assert [ln for ln in lines if ln.startswith("APP_ENV=")] == ["APP_ENV=dev"]


@pytest.mark.unit
def test_the_override_sets_only_the_seam_value_on_the_api() -> None:
    doc = yaml.safe_load(OVERRIDE.read_text(encoding="utf-8"))
    assert doc == {"services": {"api": {"environment": {SEAM: SEAM_VALUE}}}}


@pytest.mark.unit
def test_the_override_does_not_set_app_env() -> None:
    """APP_ENV=test comes from the operator's shell for the drill project only."""
    assert "APP_ENV" not in OVERRIDE.read_text(encoding="utf-8")


def _config(env_file: Path, *files: Path, app_env: str) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.isupper() or k in {"PATH", "HOME", "DOCKER_HOST"}}
    env["APP_ENV"] = app_env
    cmd = ["docker", "compose", *(a for f in files for a in ("-f", str(f)))]
    res = subprocess.run(
        [*cmd, "--env-file", str(env_file), "-p", "racket-obs05", "config", "--format", "json"],
        capture_output=True, text=True, env=env, timeout=60, check=False,
    )  # fmt: skip
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


@pytest.mark.integration
@needs_docker
def test_merged_config_differs_from_the_shipped_one_only_by_the_seam_on_the_api() -> None:
    base = _config(ENV_EXAMPLE, COMPOSE, app_env="test")
    drill = _config(ENV_EXAMPLE, COMPOSE, OVERRIDE, app_env="test")
    assert drill["services"]["api"]["environment"][SEAM] == SEAM_VALUE
    assert drill["services"]["api"]["environment"]["APP_ENV"] == "test"
    del drill["services"]["api"]["environment"][SEAM]
    assert drill == base
