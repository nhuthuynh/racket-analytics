"""ST-076a integration test (review round 1, QA-076a-R1-01): ``backup.py --once`` dumps a real
Postgres 16 (``scripts/dev-postgres.sh``) through the host ``pg_dump`` and ``age`` (NFR-045.1;
ADR 0058 rules 1 and 3; SEC-5 T5-BK-1). Binds ``tests/features/backup_service_dump.feature``.

A complete set restores: ``age -d`` of ``db.dump.age`` piped into ``pg_restore`` on a scratch
database gives the planted row back. A wrong password gives exit 1, no ``backup.json`` and
``--status`` ``missing``. No Compose: the Compose service and IT-05-03 come with ST-076a-part2.
Missing ``age`` or Postgres binaries fail, they never skip.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import pytest
from cluster import fresh_cluster
from pytest_bdd import given, parsers, scenario, then, when
from test_backup_service import SCRIPT, events, load

pytestmark = [pytest.mark.integration, pytest.mark.scenario]
FEATURE = "backup_service_dump.feature"
PG_BIN = Path("/usr/lib/postgresql/16/bin")
AGE_HEADER = b"age-encryption.org/v1\n"
ROW = "planted-row-076a"
PLANT_SQL = (
    "CREATE TABLE backup_probe (note text NOT NULL);"
    " INSERT INTO backup_probe VALUES ('planted-row-076a');"
    " CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY);"
    " INSERT INTO alembic_version VALUES ('0042_probe');"
)


@scenario(FEATURE, "An on-demand backup restores the planted row into a scratch database")
def test_backup_restores_the_planted_row() -> None:
    pass


@scenario(FEATURE, "A wrong database password leaves no complete set")
def test_wrong_password_leaves_no_complete_set() -> None:
    pass


def pg_env(url: str) -> dict[str, str]:
    u = urlsplit(url)
    return {
        "PGHOST": u.hostname or "127.0.0.1",
        "PGPORT": str(u.port or 5432),
        "PGUSER": unquote(u.username or ""),
        "PGPASSWORD": unquote(u.password or ""),
        "PGDATABASE": u.path.lstrip("/"),
    }


def tool_path() -> str:
    bindir = str(PG_BIN) if (PG_BIN / "pg_dump").exists() else ""
    path = os.pathsep.join(p for p in (bindir, os.environ.get("PATH", "")) if p)
    for tool in ("pg_dump", "pg_dumpall", "pg_restore", "psql", "age", "age-keygen"):
        if shutil.which(tool, path=path) is None:
            pytest.fail(f"{tool} not on PATH (CI installs age; the runner ships Postgres 16)")
    return path


def psql(world: dict[str, Any], sql: str, db: str | None = None) -> str:
    env = {**os.environ, **world["pg"], "PATH": world["path"]}
    if db:
        env["PGDATABASE"] = db
    p = subprocess.run(["psql", "-XAtqv", "ON_ERROR_STOP=1", "-c", sql], env=env,
                       capture_output=True, text=True, timeout=60, check=False)  # fmt: skip
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


def run_backup(world: dict[str, Any], *args: str) -> subprocess.CompletedProcess[str]:
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("BACKUP_", "PG", "S3_"))}
    env = {**clean, **world["pg"], "PATH": world["path"], "BACKUP_DIR": str(world["dir"]),
           "BACKUP_AGE_RECIPIENT": world["recipient"]}  # fmt: skip
    return subprocess.run([sys.executable, str(SCRIPT), *args], env=env, capture_output=True,
                          text=True, timeout=120, check=False)  # fmt: skip


@pytest.fixture
def world(tmp_path: Path) -> Iterator[dict[str, Any]]:
    path = tool_path()
    ident = tmp_path / "identity.txt"
    keygen = subprocess.run(["age-keygen", "-o", str(ident)], env={**os.environ, "PATH": path},
                            capture_output=True, text=True, check=True)  # fmt: skip
    with fresh_cluster(tmp_path / "pg") as url:
        yield {
            "dir": tmp_path / "backups",
            "path": path,
            "pg": pg_env(url),
            "identity": ident,
            "recipient": keygen.stderr.strip().split()[-1],
        }


@given("a live database holding a planted row")
def planted_row(world: dict[str, Any]) -> None:
    world["row"] = ROW
    psql(world, PLANT_SQL)


@given("the backup uses a wrong database password")
def wrong_password(world: dict[str, Any]) -> None:
    world["pg"] = {**world["pg"], "PGPASSWORD": "wrong-" + uuid.uuid4().hex}


@when("an on-demand backup runs against it")
def on_demand(world: dict[str, Any]) -> None:
    world["proc"] = run_backup(world, "--once")


@then(parsers.parse("the backup command exits with code {rc:d}"))
def exits(world: dict[str, Any], rc: int) -> None:
    proc = world["proc"]
    assert proc.returncode == rc, proc.stdout + proc.stderr
    run = [e for e in events(proc.stdout) if e["event"] == "backup.run"]
    assert len(run) == 1, proc.stdout
    assert run[0]["level"] == ("INFO" if rc == 0 else "ERROR")
    assert world["pg"]["PGPASSWORD"] not in proc.stdout + proc.stderr


def the_set(world: dict[str, Any]) -> Path:
    [d] = [p for p in world["dir"].iterdir() if p.is_dir()]
    return d


@then("every artefact of the new set starts with the age header")
def age_headers(world: dict[str, Any]) -> None:
    d = the_set(world)
    for name in ("globals.sql.age", "db.dump.age"):
        data = (d / name).read_bytes()
        assert data.startswith(AGE_HEADER), name
        assert b"PGDMP" not in data
        assert world["row"].encode() not in data


@then("backup.json is complete and its digests match the files")
def metadata(world: dict[str, Any]) -> None:
    bk, d = load(), the_set(world)
    meta = json.loads((d / "backup.json").read_text())
    assert meta["status"] == "complete"
    assert meta["taken_at"].endswith("Z")
    assert bk.set_name(bk.parse_set_name(d.name)) == d.name
    assert meta["taken_at"] == bk.utc_text(bk.parse_set_name(d.name))
    assert meta["alembic_revision"] == "0042_probe"
    assert meta["postgres_server_version"].startswith("16")
    assert meta["recipient"] == world["recipient"]
    for name in ("globals.sql.age", "db.dump.age"):
        assert meta["artefacts"][name] == bk.file_digest(d / name)


@then("decrypting the dump and restoring it into a scratch database returns the planted row")
def restores(world: dict[str, Any]) -> None:
    psql(world, "CREATE DATABASE scratch_restore")
    env = {**os.environ, **world["pg"], "PATH": world["path"]}
    dump = the_set(world) / "db.dump.age"
    dec = subprocess.Popen(["age", "-d", "-i", str(world["identity"]), str(dump)],
                           env=env, stdout=subprocess.PIPE)  # fmt: skip
    restore = subprocess.run(["pg_restore", "--no-owner", "-d", "scratch_restore"],
                             stdin=dec.stdout, env=env, capture_output=True, text=True,
                             timeout=120, check=False)  # fmt: skip
    assert dec.stdout
    dec.stdout.close()
    assert dec.wait(timeout=60) == 0
    assert restore.returncode == 0, restore.stderr
    assert psql(world, "SELECT note FROM backup_probe", db="scratch_restore") == world["row"]


@then("no backup.json exists")
def no_backup_json(world: dict[str, Any]) -> None:
    assert list(world["dir"].rglob("backup.json*")) == []


@then(parsers.parse('the backup status is reported as "{state}"'))
def status(world: dict[str, Any], state: str) -> None:
    proc = run_backup(world, "--status")
    assert json.loads(proc.stdout)["state"] == state, proc.stdout
    assert proc.returncode == (0 if state == "fresh" else 1)
