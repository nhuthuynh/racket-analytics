"""Self-test: each pytest session has a database of its own (C-32, PE-R3-06; C-31, PE-R2-04).

`committed_db` truncates every table before and after a test. On a database shared by two
pytest sessions (two lanes, or a verifier next to a developer) that truncate wipes the other
session's users, sessions and jobs: sign-ins turn into 401s, TRUNCATE deadlocks with live
transactions, and a worker of one session claims the other's job (`test_worker_crash` failed
2-3 of 3 tests per round when run twice in parallel on one database, decision-log 2026-10-06).

The fix: at configure time the root conftest creates a fresh database next to the one
DATABASE_URL names, points DATABASE_URL (and so the app and every worker subprocess) at it,
and drops it at the end. ``RA_TEST_DB_ISOLATION=off`` keeps the old shared behaviour.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from tests.support.db import (
    BASE_URL_ENV,
    database_url,
    make_engine,
    session_database_name,
    stale_session_databases,
)

BACKEND = Path(__file__).resolve().parents[3]


def _base_url() -> str:
    base = os.environ.get(BASE_URL_ENV, "")
    assert base, f"{BASE_URL_ENV} is not set: this session runs on the shared database"
    return base


def _current_database(engine: Any) -> str:
    with engine.connect() as conn:
        return str(conn.execute(text("SELECT current_database()")).scalar())


def _session_databases(engine: Any, base_name: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT datname FROM pg_database WHERE datname LIKE :p"),
            {"p": f"{base_name}\\_t%"},
        )
        return {str(r[0]) for r in rows}


def test_the_session_database_is_not_the_base_database(db_engine: Any) -> None:
    base_name = str(make_url(_base_url()).database)

    current = _current_database(db_engine)

    assert current != base_name
    assert current.startswith(f"{base_name}_t{os.getpid()}_")


def test_truncating_the_session_database_leaves_the_base_database_alone(
    committed_db: Any,
) -> None:
    from tests.conftest import _truncate_all

    base = make_engine(database_url_for(_base_url()))
    table = f"isolation_probe_{uuid.uuid4().hex[:8]}"
    try:
        with base.begin() as conn:
            conn.execute(text(f"CREATE TABLE {table} (id int)"))
            conn.execute(text(f"INSERT INTO {table} VALUES (1)"))

        _truncate_all(committed_db)

        with base.connect() as conn:
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar() == 1
    finally:
        with base.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        base.dispose()


def test_worker_subprocesses_inherit_the_session_database(db_engine: Any) -> None:
    # tests/support/worker.py starts `python -m racket.worker` with os.environ
    assert make_url(database_url()).database == _current_database(db_engine)


def test_the_session_database_is_dropped_when_the_session_ends(db_engine: Any) -> None:
    base_url = _base_url()
    base_name = str(make_url(base_url).database)
    before = _session_databases(db_engine, base_name)
    env = {**os.environ, "DATABASE_URL": base_url}
    env.pop(BASE_URL_ENV, None)

    child = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/integration/harness/test_db_fixture.py",
        ],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert child.returncode == 0, child.stdout[-2000:] + child.stderr[-2000:]
    left = _session_databases(db_engine, base_name) - before
    assert not [name for name in left if name in stale_session_databases(left)], left


@pytest.mark.parametrize("base", ["racket", "racket_qa", "x" * 63])
def test_session_database_names_are_valid_and_carry_the_pid(base: str) -> None:
    name = session_database_name(base, pid=4242)

    assert len(name) <= 63
    assert "_t4242_" in name
    assert name != session_database_name(base, pid=4242)  # a random suffix


def test_only_databases_of_dead_sessions_count_as_stale() -> None:
    alive = session_database_name("racket", pid=os.getpid())
    dead = session_database_name("racket", pid=2**22 + 7)  # above Linux pid_max default
    foreign = "racket_other"

    assert stale_session_databases({alive, dead, foreign}) == {dead}


def database_url_for(url: str) -> str:
    """The base URL with the psycopg driver, as the suite's engines use."""
    saved = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        return database_url()
    finally:
        if saved is not None:
            os.environ["DATABASE_URL"] = saved
