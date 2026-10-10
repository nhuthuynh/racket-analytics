"""ST-042 (SRE half; NFR-054, IT-03-10, threat model S1-F3): the media sandbox worker runs with
its own Postgres login (a member of the migration's NOLOGIN group role ``racket_media_worker``)
and its own object-store key limited to the media bucket.

Static and rendered checks here (unit); the live checks against real Postgres and SeaweedFS
from the Compose images are in ``test_compose_worker_identity_live.py``. Negative cases first.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from test_compose import COMPOSE, ENV_EXAMPLE, compose_config, needs_docker

WORKER_VARS = (
    "WORKER_DB_USER",
    "WORKER_DB_PASSWORD",
    "WORKER_S3_ACCESS_KEY_ID",
    "WORKER_S3_SECRET_ACCESS_KEY",
)


def services() -> dict:
    return yaml.safe_load(COMPOSE.read_text())["services"]


def env_example() -> dict[str, str]:
    out: dict[str, str] = {}
    for ln in ENV_EXAMPLE.read_text().splitlines():
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            out[k] = v
    return out


def rendered() -> dict:
    res = compose_config(ENV_EXAMPLE)
    assert res.returncode == 0, res.stderr
    return yaml.safe_load(res.stdout)["services"]


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_the_worker_does_not_connect_as_the_app_role() -> None:
    url = services()["worker"]["environment"]["DATABASE_URL"]
    assert "POSTGRES_USER" not in url
    assert "POSTGRES_PASSWORD" not in url
    assert "${WORKER_DB_USER:?" in url
    assert "${WORKER_DB_PASSWORD:?" in url


@pytest.mark.unit
def test_the_worker_does_not_hold_the_app_object_store_key() -> None:
    env = services()["worker"]["environment"]
    assert env["S3_ACCESS_KEY_ID"].startswith("${WORKER_S3_ACCESS_KEY_ID:?")
    assert env["S3_SECRET_ACCESS_KEY"].startswith("${WORKER_S3_SECRET_ACCESS_KEY:?")


@pytest.mark.unit
@needs_docker
@pytest.mark.parametrize("missing", WORKER_VARS)
def test_a_missing_worker_credential_stops_compose_and_names_it(
    tmp_path: Path, missing: str
) -> None:
    lines = [ln for ln in ENV_EXAMPLE.read_text().splitlines() if not ln.startswith(f"{missing}=")]
    env_file = tmp_path / "partial.env"
    env_file.write_text("\n".join(lines) + "\n")
    res = compose_config(env_file)
    assert res.returncode != 0
    assert missing in res.stderr


@pytest.mark.unit
@needs_docker
def test_rendered_worker_credentials_differ_from_the_app_ones() -> None:
    svcs = rendered()
    worker, api = svcs["worker"]["environment"], svcs["api"]["environment"]
    assert worker["DATABASE_URL"] != api["DATABASE_URL"]
    assert worker["S3_ACCESS_KEY_ID"] != api["S3_ACCESS_KEY_ID"]
    assert worker["S3_SECRET_ACCESS_KEY"] != api["S3_SECRET_ACCESS_KEY"]


@pytest.mark.unit
def test_env_example_worker_identity_is_distinct_and_a_dev_placeholder() -> None:
    env = env_example()
    for var in WORKER_VARS:
        assert env.get(var), var
    assert env["WORKER_DB_USER"] != env["POSTGRES_USER"]
    assert env["WORKER_DB_USER"] != "racket_media_worker"  # the group role is NOLOGIN
    assert env["WORKER_S3_ACCESS_KEY_ID"] != env["S3_ACCESS_KEY_ID"]
    assert "dev-only" in env["WORKER_DB_PASSWORD"]
    assert "dev-only" in env["WORKER_S3_SECRET_ACCESS_KEY"]


@pytest.mark.unit
def test_only_the_db_roles_job_and_the_worker_see_the_worker_db_password() -> None:
    for name, svc in services().items():
        text = yaml.safe_dump(svc.get("environment", {}))
        if name in {"db-roles", "worker"}:
            continue
        assert "WORKER_DB_PASSWORD" not in text, name


@pytest.mark.unit
def test_the_worker_s3_identity_is_limited_to_the_media_bucket() -> None:
    cmd = "\n".join(services()["objectstore"]["command"])
    # Two identities: the app's (unchanged) and the worker's, bucket-scoped actions only.
    assert '"name":"racket-worker"' in cmd
    after_name = cmd.split('"name":"racket-worker"', 1)[1]
    actions = after_name.split('"actions":[', 1)[1].split("]", 1)[0]
    assert '"Read:%s"' in actions, cmd
    assert '"Write:%s"' in actions, cmd
    assert '"Admin"' not in actions, cmd
    assert '"List"' not in actions, cmd


# ---------------------------------------------------------------- positive cases
@pytest.mark.unit
def test_the_api_migrate_and_mailer_keep_the_app_role() -> None:
    svcs = services()
    for name in ("api", "migrate", "mailer"):
        env = svcs[name]["environment"]
        url = env.get("DATABASE_URL") if isinstance(env, dict) else None
        if url is None:  # merged from the app-env anchor
            url = yaml.safe_load(COMPOSE.read_text())["x-required-app-env"]["DATABASE_URL"]
        assert "${POSTGRES_USER:?" in url, name


@pytest.mark.unit
def test_db_roles_runs_after_migrate_and_before_the_worker() -> None:
    svcs = services()
    roles = svcs["db-roles"]
    assert roles["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
    assert roles["restart"] == "no"
    assert svcs["worker"]["depends_on"]["db-roles"]["condition"] == (
        "service_completed_successfully"
    )
    # Same network as migrate: never on the worker's sandbox network.
    assert roles["networks"] == ["edge"]
    script = "\n".join(roles["command"]) if isinstance(roles["command"], list) else roles["command"]
    assert "racket_media_worker" in script
    assert "\\getenv" in script  # the password never appears on a command line
