"""IT-05-03 (ST-076a; NFR-045.1; ADR 0058 rules 1-3; SEC-5 T5-BK-1..3): the real ``backup``
Compose service (profile ``ops``) backs up a migrated stack, and the set restores into an empty
database.

Brings up only postgres, objectstore and objectstore-init in a project of its own with remapped
ports, applies the real migrations from the host, runs the real ``db-roles`` one-shot, seeds one
confirmed correction and one media object, then runs
``docker compose --profile ops run --rm backup --once`` with a fresh ``age`` key pair made by
the backup image itself (``age`` is not on the CI runner). The private identity stays in the
test's temp directory; the service gets the public recipient only.

The restore follows ADR 0058 rule 4 steps 3-5 on a fresh host cluster (``scripts/dev-postgres.sh``):
verify the SHA-256s, decrypt in the backup image, apply globals without the ``CREATE ROLE`` of
the cluster owner, ``pg_restore --exit-on-error --single-transaction``. Self-cleaning:
``down -v --remove-orphans`` at the end. Negative cases first.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import secrets
import subprocess
import tarfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import pytest
from botocore.exceptions import ClientError
from cluster import fresh_cluster
from conftest import REPO_ROOT
from pytest_bdd import given, scenario, then, when
from test_compose import ENV_EXAMPLE
from test_compose_worker_identity_live import Stack, denied, free_port, parse_env

pytestmark = pytest.mark.integration
USER = f"{os.getuid()}:{os.getgid()}"

ACCOUNT = "11111111-1111-4111-8111-111111111111"
MATCH = "22222222-2222-4222-8222-222222222222"
CORRECTION = "33333333-3333-4333-8333-333333333333"
OBJECT_KEY = f"matches/{MATCH}/review.mp4"
OBJECT_BODY = b"\x00\x00\x00\x18ftypmp42 IT-05-03 " + secrets.token_bytes(4096)
SEED = f"""
INSERT INTO accounts (id, created_at) VALUES ('{ACCOUNT}', now());
INSERT INTO matches (id, owner_id, title, format, status, created_at, updated_at)
  VALUES ('{MATCH}', '{ACCOUNT}', 'IT-05-03', 'doubles', 'scoring', now(), now());
INSERT INTO match_corrections (id, match_id, version, kind, actor_id, at, field, old_value, new_value)
  VALUES ('{CORRECTION}', '{MATCH}', 1, 'correction', '{ACCOUNT}', now(), 'winning_side', '"A"', '"B"');
"""


class BackupStack(Stack):
    backups: Path
    identity: Path
    recipient: str

    def backup(
        self, *args: str, entrypoint: str | None = None, extra: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        # As the test's own uid, so the runner can read and delete what the service wrote.
        run = ["--profile", "ops", "run", "--rm", "--no-deps", "-T", "-u", USER]
        if entrypoint:
            run += ["--entrypoint", entrypoint]
        return self.compose(*run, "backup", *args, extra=extra)

    def newest(self) -> Path:
        sets = sorted(p for p in self.backups.iterdir() if p.is_dir())
        assert sets, "no backup set written"
        return sets[-1]

    def decrypt(self, artefact: Path) -> bytes:
        """``age -d`` in the backup image; the identity is mounted read-only for this call only."""
        proc = subprocess.run(
            [
                *self.compose_cmd(),
                "--profile", "ops", "run", "--rm", "--no-deps", "-T", "-u", USER,
                "-v", f"{self.identity}:/run/age-identity.txt:ro",
                "-v", f"{artefact.parent}:/in:ro",
                "--entrypoint", "age", "backup", "-d", "-i", "/run/age-identity.txt", f"/in/{artefact.name}",
            ],
            capture_output=True, timeout=300, check=False, env=self.clean_env(),
        )  # fmt: skip
        assert proc.returncode == 0, proc.stderr.decode()
        return proc.stdout

    def compose_cmd(self) -> list[str]:
        return ["docker", "compose", "-p", self.project, "-f", str(REPO_ROOT / "infra" / "compose.yaml"),
                "--env-file", str(self.env_file)]  # fmt: skip

    @staticmethod
    def clean_env() -> dict[str, str]:
        return {k: v for k, v in os.environ.items() if not k.isupper() or k in {"PATH", "HOME", "DOCKER_HOST"}}


@pytest.fixture(scope="module")
def stack(tmp_path_factory: pytest.TempPathFactory) -> Iterator[BackupStack]:
    tmp = tmp_path_factory.mktemp("it0503")
    backups = tmp / "backups"
    backups.mkdir()
    env = parse_env(ENV_EXAMPLE.read_text())
    env.update(
        POSTGRES_HOST_PORT=str(free_port()),
        S3_HOST_PORT=str(free_port()),
        BACKUP_DB_PASSWORD=f"dev-only-{secrets.token_hex(8)}",
        BACKUP_S3_SECRET_ACCESS_KEY=f"dev-only-{secrets.token_hex(8)}",
        BACKUP_HOST_DIR=str(backups),
        DOCKERHUB_REGISTRY=os.environ.get("DOCKERHUB_REGISTRY", env.get("DOCKERHUB_REGISTRY", "docker.io")),
    )
    env_file = tmp / "it0503.env"
    lines = [ln for ln in ENV_EXAMPLE.read_text().splitlines() if ln.split("=", 1)[0] not in env]
    env_file.write_text("\n".join(lines + [f"{k}={v}" for k, v in env.items()]) + "\n")
    st = BackupStack(f"racket-it0503-{secrets.token_hex(4)}", env_file, env)
    st.backups = backups
    try:
        build = st.compose("--profile", "ops", "build", "backup")
        assert build.returncode == 0, build.stdout + build.stderr
        keygen = st.backup(entrypoint="age-keygen")
        assert keygen.returncode == 0, keygen.stderr
        st.identity = tmp / "age-identity.txt"
        st.identity.write_text(keygen.stdout)
        st.identity.chmod(0o600)
        m = re.search(r"^# public key: (age1\w+)$", keygen.stdout, re.M)
        assert m, keygen.stdout
        st.recipient = m.group(1)
        up = st.compose("up", "-d", "--wait", "postgres", "objectstore")
        assert up.returncode == 0, up.stderr
        init = st.compose("run", "--rm", "objectstore-init")
        assert init.returncode == 0, init.stderr
        mig = subprocess.run(
            ["uv", "run", "--project", str(REPO_ROOT / "backend"), "python", "-m", "racket.platform.migrate"],
            capture_output=True, text=True, timeout=300, check=False,
            env={**{k: v for k, v in os.environ.items() if k not in {"APP_ENV", "VIRTUAL_ENV"}},
                 "DATABASE_URL": st.app_url},
        )  # fmt: skip
        assert mig.returncode == 0, mig.stdout + mig.stderr
        roles = st.compose("run", "--rm", "--no-deps", "db-roles")
        assert roles.returncode == 0, roles.stdout + roles.stderr
        with psycopg.connect(st.app_url, autocommit=True) as conn:
            conn.execute(SEED)
        app_s3 = st.s3(env["S3_ACCESS_KEY_ID"], env["S3_SECRET_ACCESS_KEY"])
        app_s3.put_object(Bucket=env["S3_BUCKET_MEDIA"], Key=OBJECT_KEY, Body=OBJECT_BODY)
        yield st
    finally:
        st.compose("down", "-v", "--remove-orphans")


@pytest.fixture(scope="module")
def backed_up(stack: BackupStack) -> dict[str, Any]:
    proc = stack.backup("--once", extra={"BACKUP_AGE_RECIPIENT": stack.recipient})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    d = stack.newest()
    return {"proc": proc, "dir": d, "meta": json.loads((d / "backup.json").read_text())}


# ---------------------------------------------------------------- negative cases first
def test_backup_login_cannot_write_a_row(stack: BackupStack) -> None:
    """T5-BK-3: `pg_read_all_data` only."""
    url = stack.url(stack.env["BACKUP_DB_USER"], stack.env["BACKUP_DB_PASSWORD"])
    assert denied(url, f"INSERT INTO accounts (id, created_at) VALUES ('{secrets.token_hex(4)}0000-0000-4000-8000-000000000000', now())")  # noqa: S608
    assert denied(url, "DELETE FROM alembic_version")


def test_backup_store_key_cannot_write_or_delete_media(stack: BackupStack) -> None:
    """T5-BK-3: Read and List on the media bucket only."""
    s3 = stack.s3(stack.env["BACKUP_S3_ACCESS_KEY_ID"], stack.env["BACKUP_S3_SECRET_ACCESS_KEY"])
    bucket = stack.env["S3_BUCKET_MEDIA"]
    with pytest.raises(ClientError):
        s3.put_object(Bucket=bucket, Key="planted-by-backup-key", Body=b"x")
    with pytest.raises(ClientError):
        s3.delete_object(Bucket=bucket, Key=OBJECT_KEY)
    assert s3.get_object(Bucket=bucket, Key=OBJECT_KEY)["Body"].read() == OBJECT_BODY


def test_without_a_recipient_the_service_exits_2_and_writes_no_set(stack: BackupStack) -> None:
    before = sorted(stack.backups.iterdir())
    proc = stack.backup("--once")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "BACKUP_AGE_RECIPIENT" in proc.stdout + proc.stderr
    assert sorted(stack.backups.iterdir()) == before


def test_no_artefact_is_plaintext_and_no_temp_file_remains(backed_up: dict[str, Any]) -> None:
    """T5-BK-1: every artefact starts with the age header; nothing else is in the set."""
    d: Path = backed_up["dir"]
    assert sorted(p.name for p in d.iterdir()) == ["backup.json", "db.dump.age", "globals.sql.age", "objects.tar.age"]
    for name in ("db.dump.age", "globals.sql.age", "objects.tar.age"):
        head = (d / name).read_bytes()[:32]
        assert head.startswith(b"age-encryption.org/v1"), name
        assert b"PGDMP" not in (d / name).read_bytes(), name


def test_decrypting_without_the_identity_fails(stack: BackupStack, backed_up: dict[str, Any]) -> None:
    proc = stack.backup("-d", "/backups/" + backed_up["dir"].name + "/db.dump.age", entrypoint="age")
    assert proc.returncode != 0


# ---------------------------------------------------------------- metadata (rule 1)
def test_metadata_is_complete_utc_and_matches_the_artefacts(stack: BackupStack, backed_up: dict[str, Any]) -> None:
    meta, d = backed_up["meta"], backed_up["dir"]
    assert meta["schema_version"] == 1
    assert meta["status"] == "complete"
    assert meta["taken_at"].endswith("Z") and d.name == datetime.fromisoformat(meta["taken_at"]).strftime("%Y%m%dT%H%M%SZ")
    assert meta["alembic_revision"] == "0021"
    assert meta["postgres_server_version"].startswith("16")
    assert meta["recipient"] == stack.recipient
    assert meta["image_tag"] == "dev"
    for name, digest in meta["artefacts"].items():
        data = (d / name).read_bytes()
        assert digest == {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}, name
    assert meta["objects"]["count"] == 1
    assert "@" not in json.dumps(meta), "backup.json holds no personal data"


def test_status_reads_the_metadata_age_as_fresh(stack: BackupStack, backed_up: dict[str, Any]) -> None:
    proc = stack.backup("--status")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["state"] == "fresh"
    assert report["newest_complete"] == backed_up["dir"].name
    assert 0 <= report["age_s"] < 600


def test_the_run_logs_json_lines_without_secrets(stack: BackupStack, backed_up: dict[str, Any]) -> None:
    out = backed_up["proc"].stdout
    lines = [json.loads(ln) for ln in out.splitlines() if ln.startswith("{")]
    run = [e for e in lines if e["event"] == "backup.run"]
    assert run[-1]["status"] == "complete" and run[-1]["duration_ms"] >= 0
    assert run[-1]["last_complete_at"] == backed_up["meta"]["taken_at"]
    assert any(e["event"] == "backup.retention" for e in lines)
    for secret in (stack.env["BACKUP_DB_PASSWORD"], stack.env["BACKUP_S3_SECRET_ACCESS_KEY"], OBJECT_KEY):
        assert secret not in out + backed_up["proc"].stderr


# ---------------------------------------------------------------- the restore (IT-05-03)
def restore(stack: BackupStack, d: Path, tmp: Path) -> Iterator[str]:
    meta = json.loads((d / "backup.json").read_text())
    for name, digest in meta["artefacts"].items():  # rule 3: verify before decrypting
        assert hashlib.sha256((d / name).read_bytes()).hexdigest() == digest["sha256"], name
    globals_sql = stack.decrypt(d / "globals.sql.age").decode()
    owner = stack.env["POSTGRES_USER"]
    globals_sql = "\n".join(ln for ln in globals_sql.splitlines() if ln.strip() != f"CREATE ROLE {owner};")
    dump = tmp / "db.dump"
    dump.write_bytes(stack.decrypt(d / "db.dump.age"))
    with fresh_cluster(tmp / "scratch-pg") as url:
        g = subprocess.run(["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", url], input=globals_sql,
                           capture_output=True, text=True, timeout=120, check=False)  # fmt: skip
        assert g.returncode == 0, g.stderr
        r = subprocess.run(["pg_restore", "--exit-on-error", "--single-transaction", "-d", url, str(dump)],
                           capture_output=True, text=True, timeout=300, check=False)  # fmt: skip
        assert r.returncode == 0, r.stderr
        dump.unlink()
        yield url


def test_the_set_restores_into_an_empty_database(stack: BackupStack, backed_up: dict[str, Any], tmp_path: Path) -> None:
    for url in restore(stack, backed_up["dir"], tmp_path):
        with psycopg.connect(url) as conn:
            assert conn.execute("SELECT version_num FROM alembic_version").fetchone() == ("0021",)
            assert conn.execute("SELECT id::text FROM match_corrections").fetchall() == [(CORRECTION,)]
            triggers = conn.execute(
                "SELECT count(*) FROM pg_trigger WHERE tgrelid = 'match_corrections'::regclass AND NOT tgisinternal"
            ).fetchone()
            assert triggers and triggers[0] >= 2, "the append-only triggers come back with the data"
            with pytest.raises(psycopg.Error):
                conn.execute(f"DELETE FROM match_corrections WHERE id = '{CORRECTION}'")  # noqa: S608


def test_the_object_mirror_holds_every_object_with_its_sha256(stack: BackupStack, backed_up: dict[str, Any]) -> None:
    raw = stack.decrypt(backed_up["dir"] / "objects.tar.age")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tar:
        names = tar.getnames()
        manifest_member = tar.extractfile("objects.manifest.json")
        assert manifest_member is not None
        manifest_bytes = manifest_member.read()
        body = tar.extractfile(f"objects/{OBJECT_KEY}")
        assert body is not None and body.read() == OBJECT_BODY
    assert names[-1] == "objects.manifest.json"
    manifest = json.loads(manifest_bytes)
    assert manifest == {"objects": [{"key": OBJECT_KEY, "size": len(OBJECT_BODY), "sha256": hashlib.sha256(OBJECT_BODY).hexdigest()}]}
    assert backed_up["meta"]["objects"]["sha256"] == hashlib.sha256(manifest_bytes).hexdigest()


# ---------------------------------------------------------------- Gherkin binding
@scenario("backup_service.feature", "A backup of the Compose stack restores into an empty database")
def test_compose_backup_restores() -> None:
    pass


@given("the Compose stack with one confirmed correction and one media object")
def given_stack(stack: BackupStack) -> BackupStack:
    return stack


@when("an on-demand backup runs in the backup service", target_fixture="run")
def when_backup(backed_up: dict[str, Any]) -> dict[str, Any]:
    return backed_up


@then("the newest set is complete, fresh and holds no plaintext dump")
def then_complete(stack: BackupStack, run: dict[str, Any]) -> None:
    test_no_artefact_is_plaintext_and_no_temp_file_remains(run)
    test_status_reads_the_metadata_age_as_fresh(stack, run)


@then("the set restores into an empty database with the correction and its append-only triggers")
def then_restores(stack: BackupStack, run: dict[str, Any], tmp_path: Path) -> None:
    test_the_set_restores_into_an_empty_database(stack, run, tmp_path)


@then("the object mirror holds the media object with its SHA-256")
def then_objects(stack: BackupStack, run: dict[str, Any]) -> None:
    test_the_object_mirror_holds_every_object_with_its_sha256(stack, run)
