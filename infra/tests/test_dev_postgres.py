"""ST-001: scripts/dev-postgres.sh starts a throwaway Postgres 16 without Docker and prints a
DATABASE_URL. Real server, real TCP, real password auth: no SQLite, no mocks [AQS/OPS-05]."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import psycopg
import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.integration

SCRIPT = SCRIPTS_DIR / "dev-postgres.sh"


def pg(
    cmd: str, state: Path, extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "RA_DEV_STATE": str(state), **(extra or {})}
    return subprocess.run(
        ["bash", str(SCRIPT), cmd],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )


def url_from(stdout: str) -> str:
    m = re.search(r"^export DATABASE_URL=(\S+)$", stdout, re.MULTILINE)
    assert m, stdout
    return m.group(1)


@pytest.fixture
def state(tmp_path: Path):
    s = tmp_path / "state"
    yield s
    pg("stop", s)


def test_missing_postgres_binaries_fail_with_a_clear_message(state: Path) -> None:
    res = pg("start", state, {"PG_BIN": "/nonexistent/bin"})
    assert res.returncode != 0
    assert "initdb not found" in res.stderr


def test_start_prints_a_working_database_url_for_postgres_16(state: Path) -> None:
    res = pg("start", state)
    assert res.returncode == 0, res.stderr
    url = url_from(res.stdout)
    assert url.startswith("postgresql://")
    with psycopg.connect(url, connect_timeout=5) as conn:
        version = conn.execute("show server_version").fetchone()[0]
    assert version.startswith("16")


def test_password_auth_is_enforced_over_tcp(state: Path) -> None:
    url = url_from(pg("start", state).stdout)
    wrong = re.sub(r"://([^:]+):[^@]+@", r"://\1:wrong@", url)
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(wrong, connect_timeout=5)


def test_second_start_is_idempotent(state: Path) -> None:
    first = url_from(pg("start", state).stdout)
    second = pg("start", state)
    assert second.returncode == 0
    assert url_from(second.stdout) == first


def test_two_clusters_get_different_ports(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    try:
        ua, ub = url_from(pg("start", a).stdout), url_from(pg("start", b).stdout)
        assert ua != ub
    finally:
        pg("stop", a)
        pg("stop", b)


def test_stop_shuts_down_and_removes_the_data(state: Path) -> None:
    url = url_from(pg("start", state).stdout)
    data_dir = Path(re.search(r"^# PGDATA=(\S+)$", pg("url", state).stdout, re.M).group(1))
    assert data_dir.is_dir()
    assert pg("stop", state).returncode == 0
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(url, connect_timeout=2)
    assert not data_dir.exists()


def test_url_without_a_running_cluster_fails(state: Path) -> None:
    res = pg("url", state)
    assert res.returncode != 0
    assert "not running" in res.stderr
