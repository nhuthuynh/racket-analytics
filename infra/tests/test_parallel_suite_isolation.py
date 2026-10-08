"""CI-PERF-GATES integration (NFR-073): the backend suite runs in parallel workers, each on its
own database, against a real Postgres 16 from ``scripts/dev-postgres.sh`` (no mocks).

Runs the backend's database-harness tests (``tests/integration/harness``: session database
isolation, truncation, worker subprocess inheritance) with ``pytest -n 2``. Every worker must
create its own session database (C-32) and drop it at the end, so a parallel run leaves the
base database and the server exactly as it found them. Needs ``uv`` (CI installs it).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import psycopg
import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR

pytestmark = pytest.mark.integration

BACKEND = REPO_ROOT / "backend"
HARNESS = ["tests/integration/harness/test_db_isolation.py",
           "tests/integration/harness/test_db_fixture.py"]  # fmt: skip


@pytest.fixture
def database_url(tmp_path: Path):  # noqa: ANN201 - yields the URL of a throwaway Postgres
    env = {**os.environ, "RA_DEV_STATE": str(tmp_path / "pg")}
    start = subprocess.run(["bash", str(SCRIPTS_DIR / "dev-postgres.sh"), "start"], env=env,
                           capture_output=True, text=True, timeout=120, check=False)  # fmt: skip
    assert start.returncode == 0, start.stderr
    m = re.search(r"^export DATABASE_URL=(\S+)$", start.stdout, re.MULTILINE)
    assert m, start.stdout
    try:
        yield m.group(1)
    finally:
        subprocess.run(["bash", str(SCRIPTS_DIR / "dev-postgres.sh"), "stop"], env=env,
                       capture_output=True, timeout=120, check=False)  # fmt: skip


def _databases(url: str) -> set[str]:
    with psycopg.connect(url, connect_timeout=5) as conn:
        return {r[0] for r in conn.execute("SELECT datname FROM pg_database").fetchall()}


def test_two_workers_each_get_and_drop_their_own_database(database_url: str) -> None:
    if shutil.which("uv") is None:
        pytest.fail("uv not on PATH (CI: pip install uv) - fails closed, no skip")
    before = _databases(database_url)
    env = {**os.environ, "DATABASE_URL": database_url, "APP_ENV": "test"}
    env.pop("VIRTUAL_ENV", None)  # the infra venv must not leak into the backend project
    res = subprocess.run(
        ["uv", "run", "--locked", "pytest", "-q", "-p", "no:cacheprovider", "-n", "2",
         *HARNESS],
        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=600, check=False,
    )  # fmt: skip
    out = res.stdout + res.stderr
    assert res.returncode == 0, out[-3000:]
    assert re.search(r"created: 2/2 workers|2 workers \[", out), out[-3000:]
    assert " passed" in out and " failed" not in out
    assert _databases(database_url) == before  # every worker dropped its session database
