"""ST-042 live (SRE half; IT-03-10 on the Compose services; NFR-054).

Brings up only the pulled Compose services (postgres, objectstore, objectstore-init) in a
project of its own with remapped ports, applies the real migrations from the host, runs the
real ``db-roles`` one-shot, then connects with the worker's own login and S3 key:

- the worker login cannot read ``sessions``, ``sign_in_*`` or ``accounts`` (permission denied);
- it can read and update ``jobs`` (the probe stage's grants) and cannot enqueue;
- ``db-roles`` is idempotent, rotates the password, and refuses to touch the app role;
- the worker's S3 key reads and writes the media bucket only.

Self-cleaning: ``down -v --remove-orphans`` at the end (ADR 0033 rule 3). Negative cases first.
"""

from __future__ import annotations

import os
import secrets
import shutil
import socket
import subprocess
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import boto3
import psycopg
import pytest
from botocore.client import Config
from botocore.exceptions import ClientError
from conftest import REPO_ROOT
from test_compose import COMPOSE, ENV_EXAMPLE

pytestmark = pytest.mark.integration


def _docker_up() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0


if not _docker_up():  # pragma: no cover - environment dependent
    pytest.skip("needs a running Docker daemon", allow_module_level=True)


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@dataclass
class Stack:
    project: str
    env_file: Path
    env: dict[str, str]

    def compose(
        self, *args: str, extra: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        clean = {
            k: v
            for k, v in os.environ.items()
            if not k.isupper() or k in {"PATH", "HOME", "DOCKER_HOST"}
        }
        cmd = [
            "docker",
            "compose",
            "-p",
            self.project,
            "-f",
            str(COMPOSE),
            "--env-file",
            str(self.env_file),
        ]
        if extra:
            run_args = list(args)
            idx = run_args.index("run") + 1
            for k, v in extra.items():
                run_args[idx:idx] = ["-e", f"{k}={v}"]
            args = tuple(run_args)
        return subprocess.run(
            [*cmd, *args], capture_output=True, text=True, env=clean, timeout=300, check=False
        )

    def url(self, user: str, password: str) -> str:
        return f"postgresql://{user}:{password}@127.0.0.1:{self.env['POSTGRES_HOST_PORT']}/{self.env['POSTGRES_DB']}"

    @property
    def app_url(self) -> str:
        return self.url(self.env["POSTGRES_USER"], self.env["POSTGRES_PASSWORD"])

    @property
    def worker_url(self) -> str:
        return self.url(self.env["WORKER_DB_USER"], self.env["WORKER_DB_PASSWORD"])

    def s3(self, key: str, secret: str):  # boto3 client type is dynamic
        return boto3.client(
            "s3",
            endpoint_url=f"http://127.0.0.1:{self.env['S3_HOST_PORT']}",
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            region_name=self.env["S3_REGION"],
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )


def parse_env(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for ln in text.splitlines():
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            out[k] = v
    return out


@pytest.fixture(scope="module")
def stack(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Stack]:
    tmp = tmp_path_factory.mktemp("st042")
    env = parse_env(ENV_EXAMPLE.read_text())
    env.update(
        POSTGRES_HOST_PORT=str(free_port()),
        S3_HOST_PORT=str(free_port()),
        WORKER_DB_PASSWORD=f"dev-only-{secrets.token_hex(8)}",
        WORKER_S3_SECRET_ACCESS_KEY=f"dev-only-{secrets.token_hex(8)}",
        DOCKERHUB_REGISTRY=os.environ.get(
            "DOCKERHUB_REGISTRY", env.get("DOCKERHUB_REGISTRY", "docker.io")
        ),
    )
    env_file = tmp / "st042.env"
    lines = [ln for ln in ENV_EXAMPLE.read_text().splitlines() if ln.split("=", 1)[0] not in env]
    env_file.write_text("\n".join(lines + [f"{k}={v}" for k, v in env.items()]) + "\n")
    st = Stack(f"racket-st042-{uuid.uuid4().hex[:8]}", env_file, env)
    try:
        up = st.compose("up", "-d", "--wait", "postgres", "objectstore")
        assert up.returncode == 0, up.stderr
        init = st.compose("run", "--rm", "objectstore-init")
        assert init.returncode == 0, init.stderr
        mig = subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(REPO_ROOT / "backend"),
                "python",
                "-m",
                "racket.platform.migrate",
            ],
            capture_output=True,
            text=True,
            env={
                **{k: v for k, v in os.environ.items() if k not in {"APP_ENV", "VIRTUAL_ENV"}},
                "DATABASE_URL": st.app_url,
            },
            timeout=300,
            check=False,
        )
        assert mig.returncode == 0, mig.stdout + mig.stderr
        roles = st.compose("run", "--rm", "--no-deps", "db-roles")
        assert roles.returncode == 0, roles.stdout + roles.stderr
        yield st
    finally:
        st.compose("down", "-v", "--remove-orphans")


def denied(url: str, sql: str) -> bool:
    with psycopg.connect(url, autocommit=True) as conn:
        try:
            conn.execute(sql)
        except psycopg.errors.InsufficientPrivilege:
            return True
    return False


# ---------------------------------------------------------------- negative cases first
def test_worker_login_cannot_read_identity_tables(stack: Stack) -> None:
    with psycopg.connect(stack.app_url) as conn:
        sign_in = [
            r[0]
            for r in conn.execute(
                "select table_name from information_schema.tables "
                "where table_schema='public' and table_name like 'sign_in%'"
            )
        ]
    assert sign_in, "expected sign_in_* tables from the migrations"
    for table in ["sessions", "accounts", *sign_in]:
        assert denied(stack.worker_url, f"select 1 from {table} limit 1"), table  # noqa: S608 - names from pg_catalog


def test_worker_login_cannot_enqueue_jobs_or_read_the_scorebook(stack: Stack) -> None:
    assert denied(stack.worker_url, "insert into jobs default values")
    with psycopg.connect(stack.app_url) as conn:
        tables = {
            r[0] for r in conn.execute("select tablename from pg_tables where schemaname='public'")
        }
    scorebook = {"match_rallies", "match_games", "match_corrections", "rate_limit_events"}
    assert scorebook <= tables
    for table in sorted(scorebook):
        assert denied(stack.worker_url, f"select 1 from {table} limit 1"), table  # noqa: S608 - names from pg_catalog


def test_worker_login_has_no_admin_attributes(stack: Stack) -> None:
    with psycopg.connect(stack.app_url) as conn:
        row = conn.execute(
            "select rolsuper, rolcreatedb, rolcreaterole, rolbypassrls, rolinherit, rolcanlogin "
            "from pg_roles where rolname = %s",
            (stack.env["WORKER_DB_USER"],),
        ).fetchone()
        member = conn.execute(
            "select pg_has_role(%s, 'racket_media_worker', 'USAGE')", (stack.env["WORKER_DB_USER"],)
        ).fetchone()
    assert row == (False, False, False, False, True, True)
    assert member == (True,)


def test_db_roles_refuses_the_app_role_as_the_worker_login(stack: Stack) -> None:
    res = stack.compose(
        "run", "--rm", "--no-deps", "db-roles", extra={"WORKER_DB_USER": stack.env["POSTGRES_USER"]}
    )
    assert res.returncode != 0
    assert "must not be the app role" in res.stdout + res.stderr
    with psycopg.connect(stack.app_url) as conn:
        assert conn.execute(
            "select rolsuper from pg_roles where rolname = current_user"
        ).fetchone() == (True,)


def test_db_roles_refuses_a_name_that_is_not_a_plain_identifier(stack: Stack) -> None:
    res = stack.compose(
        "run", "--rm", "--no-deps", "db-roles", extra={"WORKER_DB_USER": 'x"; drop'}
    )
    assert res.returncode != 0


def test_worker_s3_key_cannot_touch_another_bucket(stack: Stack) -> None:
    app = stack.s3(stack.env["S3_ACCESS_KEY_ID"], stack.env["S3_SECRET_ACCESS_KEY"])
    worker = stack.s3(
        stack.env["WORKER_S3_ACCESS_KEY_ID"], stack.env["WORKER_S3_SECRET_ACCESS_KEY"]
    )
    other = "racket-other"
    app.create_bucket(Bucket=other)
    app.put_object(Bucket=other, Key="secret.txt", Body=b"x")
    with pytest.raises(ClientError):
        worker.get_object(Bucket=other, Key="secret.txt")
    with pytest.raises(ClientError):
        worker.put_object(Bucket=other, Key="w.txt", Body=b"x")
    with pytest.raises(ClientError):
        worker.delete_object(Bucket=other, Key="secret.txt")
    assert app.head_object(Bucket=other, Key="secret.txt")["ContentLength"] == 1
    with pytest.raises(ClientError):
        worker.create_bucket(Bucket="racket-worker-made")


def test_a_wrong_worker_secret_is_refused(stack: Stack) -> None:
    bad = stack.s3(stack.env["WORKER_S3_ACCESS_KEY_ID"], "wrong-secret")
    with pytest.raises(ClientError):
        bad.get_object(Bucket=stack.env["S3_BUCKET_MEDIA"], Key="anything")


# ---------------------------------------------------------------- positive cases
def test_worker_login_reads_and_updates_jobs(stack: Stack) -> None:
    with psycopg.connect(stack.worker_url, autocommit=True) as conn:
        conn.execute("select count(*) from jobs").fetchone()
        conn.execute("update jobs set attempts = attempts where false")
        conn.execute("select count(*) from media_assets").fetchone()
        conn.execute("select count(*) from upload_sessions").fetchone()


def test_db_roles_is_idempotent_and_rotates_the_password(stack: Stack) -> None:
    new = f"dev-only-{secrets.token_hex(8)}"
    res = stack.compose("run", "--rm", "--no-deps", "db-roles", extra={"WORKER_DB_PASSWORD": new})
    assert res.returncode == 0, res.stdout + res.stderr
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(stack.worker_url, connect_timeout=5)
    with psycopg.connect(stack.url(stack.env["WORKER_DB_USER"], new)) as conn:
        assert conn.execute("select current_user").fetchone() == (stack.env["WORKER_DB_USER"],)
    res = stack.compose("run", "--rm", "--no-deps", "db-roles")  # back to the env file's value
    assert res.returncode == 0, res.stdout + res.stderr
    with psycopg.connect(stack.worker_url) as conn:
        conn.execute("select 1")


def test_worker_s3_key_reads_writes_and_deletes_in_the_media_bucket(stack: Stack) -> None:
    worker = stack.s3(
        stack.env["WORKER_S3_ACCESS_KEY_ID"], stack.env["WORKER_S3_SECRET_ACCESS_KEY"]
    )
    bucket = stack.env["S3_BUCKET_MEDIA"]
    key = f"originals/{uuid.uuid4().hex}"
    worker.put_object(Bucket=bucket, Key=key, Body=b"probe")
    assert worker.head_object(Bucket=bucket, Key=key)["ContentLength"] == 5
    assert worker.get_object(Bucket=bucket, Key=key, Range="bytes=0-1")["Body"].read() == b"pr"
    worker.delete_object(Bucket=bucket, Key=key)
    with pytest.raises(ClientError):
        worker.head_object(Bucket=bucket, Key=key)


def test_the_app_key_keeps_full_access(stack: Stack) -> None:
    app = stack.s3(stack.env["S3_ACCESS_KEY_ID"], stack.env["S3_SECRET_ACCESS_KEY"])
    names = {b["Name"] for b in app.list_buckets()["Buckets"]}
    assert stack.env["S3_BUCKET_MEDIA"] in names
