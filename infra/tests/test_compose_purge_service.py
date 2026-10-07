"""SRE-PURGE slice (b) (ADR 0038 Accepted; NFR-066 c, NFR-054; goal G03-03 c): the scheduled
purge/expiry job runs as its own Compose service ``purge``.

It is built from the API image (no ffprobe), runs ``infra/docker/purge_schedule.py`` around
``python -m racket.platform.purge --once``, holds the app identity (never the media sandbox
worker's login or key, ST-042), is not on the ``sandbox`` network, is hardened like the mailer,
and renders ``PURGE_INTERVAL_S`` at most one day. Negative cases first.
"""

from __future__ import annotations

import pytest
import yaml
from test_compose import COMPOSE, ENV_EXAMPLE, compose_config, needs_docker

JOB = ["python", "-m", "racket.platform.purge", "--once"]


def services() -> dict:
    return yaml.safe_load(COMPOSE.read_text())["services"]


def purge() -> dict:
    svc = services().get("purge")
    assert svc is not None, "no `purge` service in infra/compose.yaml (ADR 0038)"
    return svc


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_purge_does_not_use_the_media_sandbox_identity_or_network() -> None:
    svc = purge()
    env = svc["environment"]
    assert "WORKER_DB_USER" not in env["DATABASE_URL"]
    assert "${POSTGRES_USER:?" in env["DATABASE_URL"]
    assert env["S3_ACCESS_KEY_ID"].startswith("${S3_ACCESS_KEY_ID:?")
    assert env["S3_SECRET_ACCESS_KEY"].startswith("${S3_SECRET_ACCESS_KEY:?")
    assert "sandbox" not in svc["networks"]
    assert svc["networks"] == ["edge"]
    assert not svc.get("ports"), "the purge job serves nothing"


@pytest.mark.unit
def test_purge_is_hardened_like_the_mailer() -> None:
    svc = purge()
    assert svc["read_only"] is True
    assert svc["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in svc["security_opt"]
    assert any(t.startswith("/tmp") for t in svc["tmpfs"])
    assert svc["stop_signal"] == "SIGTERM"


# ---------------------------------------------------------------- positive cases
@pytest.mark.unit
def test_purge_runs_the_job_under_the_scheduler_from_the_api_image() -> None:
    svc = purge()
    assert svc["build"]["target"] == "api"
    assert svc["build"]["dockerfile"] == "infra/docker/backend.Dockerfile"
    assert svc["command"] == ["python", "/opt/racket/purge_schedule.py", *JOB]
    assert svc["restart"] == "unless-stopped"
    assert svc["environment"]["OTEL_SERVICE_NAME"] == "racket-purge"
    assert "purge-heartbeat" in " ".join(svc["healthcheck"]["test"])


@pytest.mark.unit
def test_purge_waits_for_migrations_database_and_bucket() -> None:
    deps = purge()["depends_on"]
    assert deps["postgres"]["condition"] == "service_healthy"
    assert deps["migrate"]["condition"] == "service_completed_successfully"
    assert deps["objectstore-init"]["condition"] == "service_completed_successfully"


@pytest.mark.unit
@needs_docker
def test_rendered_purge_interval_is_at_most_a_day() -> None:
    res = compose_config(ENV_EXAMPLE)
    assert res.returncode == 0, res.stderr
    env = yaml.safe_load(res.stdout)["services"]["purge"]["environment"]
    interval = env["PURGE_INTERVAL_S"]
    assert str(interval).isdigit()
    assert 1 <= int(interval) <= 86400
    assert "PURGE_INTERVAL_S" in res.stdout  # G03-03 (c) greps the rendered config
