"""Least privilege between the Compose app services (SEC-R5-S1-01, threat model S1-F3, v0 F-1).

The mailer only sends the sign-in email (ADR 0027): it never reads or writes media, so it must
not hold the object-store key. The separate database role and S3 key for the sandboxed worker
are deferred to ST-042 (decision-log 2026-10-05, gate before any non-dev deployment).
"""

from __future__ import annotations

import pytest
import yaml
from test_compose import COMPOSE, ENV_EXAMPLE, compose_config, needs_docker

S3_KEYS = ("S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY")


def services() -> dict:
    return yaml.safe_load(COMPOSE.read_text())["services"]


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_the_mailer_holds_no_object_store_key() -> None:
    env = services()["mailer"]["environment"]
    for key in S3_KEYS:
        assert key not in env, key


@pytest.mark.unit
@needs_docker
def test_the_rendered_mailer_has_no_object_store_key() -> None:
    res = compose_config(ENV_EXAMPLE)
    assert res.returncode == 0, res.stderr
    env = yaml.safe_load(res.stdout)["services"]["mailer"]["environment"]
    for key in S3_KEYS:
        assert key not in env, key


# ---------------------------------------------------------------- positive cases
@pytest.mark.unit
def test_media_services_keep_the_object_store_key() -> None:
    svcs = services()
    for name in ("api", "worker"):
        env = svcs[name]["environment"]
        for key in S3_KEYS:
            assert key in env, (name, key)


@pytest.mark.unit
def test_the_mailer_keeps_the_settings_it_needs_to_start() -> None:
    # Settings.from_env requires S3_BUCKET_MEDIA and DATABASE_URL in every process.
    env = services()["mailer"]["environment"]
    assert "S3_BUCKET_MEDIA" in env
    assert "DATABASE_URL" in env
