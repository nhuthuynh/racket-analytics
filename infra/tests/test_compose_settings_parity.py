"""SRE-VERIFY04R3-02 unit tests: the env.example -> Compose parity check (retro C2/C3).

Negative cases first: each rule fails on a planted copy before the shipped files are checked.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from compose_env_parity import (
    HOST_ONLY,
    NON_READERS,
    SETTINGS_READERS,
    check,
    env_example,
    settings_names,
)
from conftest import REPO_ROOT
from test_compose import COMPOSE, ENV_EXAMPLE

SETTINGS_PY = REPO_ROOT / "backend" / "src" / "racket" / "platform" / "settings.py"
SPRINT4 = (
    "FEATURE_AGE_GATE", "FEATURE_RETENTION_SETTING", "FEATURE_TRAINING_CONSENT", "FEATURE_QUOTAS",
    "COACHING_WEAKNESS_UNIT", "AGE_MINIMUM", "RETENTION_CHOICES_DAYS", "RETENTION_DEFAULT_DAYS",
    "MATCH_CREATIONS_PER_HOUR", "MATCH_CREATIONS_PER_IP_PER_HOUR", "STORAGE_QUOTA_BYTES",
)  # fmt: skip


def copies(tmp_path: Path, env: str = "", compose: str | None = None, settings: str = "") -> list:
    e, c, s = tmp_path / "env", tmp_path / "compose.yaml", tmp_path / "settings.py"
    e.write_text(ENV_EXAMPLE.read_text() + env)
    c.write_text(COMPOSE.read_text() if compose is None else compose)
    s.write_text(SETTINGS_PY.read_text() + settings)
    return check(e, c, s)


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_a_planted_setting_in_env_example_that_compose_never_uses_fails(tmp_path: Path) -> None:
    problems = copies(tmp_path, env="PLANTED_HOST_THING=1\n")
    assert "PLANTED_HOST_THING: in env.example but not forwarded to any Compose service" in problems


@pytest.mark.unit
def test_a_setting_forwarded_to_the_api_only_fails_for_the_other_readers(tmp_path: Path) -> None:
    compose = COMPOSE.read_text().replace(
        "      OTEL_SERVICE_NAME: racket-api\n",
        "      OTEL_SERVICE_NAME: racket-api\n      FEATURE_PLANTED: ${FEATURE_PLANTED:-false}\n",
    )
    problems = copies(
        tmp_path, "FEATURE_PLANTED=false\n", compose, '\nX = boolean("FEATURE_PLANTED")\n'
    )
    assert problems == [
        f"FEATURE_PLANTED: read by Settings but not forwarded to {s}"
        for s in SETTINGS_READERS
        if s != "api"
    ]


@pytest.mark.unit
def test_a_hard_coded_value_is_not_forwarding(tmp_path: Path) -> None:
    compose = COMPOSE.read_text().replace("${FEATURE_QUOTAS:-false}", "false")
    problems = copies(tmp_path, compose=compose)
    assert "FEATURE_QUOTAS: read by Settings but not forwarded to api" in problems


@pytest.mark.unit
def test_a_fallback_that_differs_from_env_example_fails(tmp_path: Path) -> None:
    compose = COMPOSE.read_text().replace("${AGE_MINIMUM:-18}", "${AGE_MINIMUM:-21}")
    problems = copies(tmp_path, compose=compose)
    assert any("AGE_MINIMUM" in p and "'21'" in p and "'18'" in p for p in problems), problems


@pytest.mark.unit
def test_host_only_cannot_hide_a_setting_the_backend_reads(tmp_path: Path) -> None:
    problems = copies(tmp_path, settings='\nX = optional("BILLING_ALERT_RECEIVER_URL_FILE")\n')
    assert problems == [
        "BILLING_ALERT_RECEIVER_URL_FILE: in HOST_ONLY but the backend Settings reads it"
    ]


# ---------------------------------------------------------------- the shipped files
@pytest.mark.unit
def test_shipped_env_example_and_compose_are_in_parity() -> None:
    assert check(ENV_EXAMPLE, COMPOSE, SETTINGS_PY) == []


@pytest.mark.unit
@pytest.mark.parametrize("name", SPRINT4)
def test_sprint4_setting_is_read_by_settings_and_in_env_example(name: str) -> None:
    assert name in settings_names(SETTINGS_PY)
    assert name in env_example(ENV_EXAMPLE)


@pytest.mark.unit
def test_flags_fall_back_to_off_in_compose() -> None:
    text = COMPOSE.read_text()
    for flag in (n for n in SPRINT4 if n.startswith("FEATURE_")):
        assert "${" + flag + ":-false}" in text, flag


@pytest.mark.unit
def test_every_backend_image_service_is_classified() -> None:
    services = yaml.safe_load(COMPOSE.read_text())["services"]
    backend = {
        name
        for name, svc in services.items()
        if "backend.Dockerfile" in str((svc.get("build") or {}).get("dockerfile", ""))
    }
    assert backend == set(SETTINGS_READERS) | set(NON_READERS)


@pytest.mark.unit
def test_host_only_settings_are_in_env_example_and_used_by_the_billing_renderer() -> None:
    renderer = (REPO_ROOT / "infra" / "observability" / "billing_budgets.py").read_text()
    for name in HOST_ONLY:
        assert name in env_example(ENV_EXAMPLE), name
        assert f'"{name}"' in renderer, name
