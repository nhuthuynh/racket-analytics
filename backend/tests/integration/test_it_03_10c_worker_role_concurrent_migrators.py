"""IT-03-10c (ST-042; NFR-073): migration 0012 creates the cluster-wide role safely when two
migrators run it at the same moment.

Roles are cluster-wide, but the migration lock (``pg_advisory_lock``) is per database, so
parallel test workers (``pytest -n``) and API replicas migrating their own databases of one
cluster can both pass 0012's ``NOT EXISTS`` check. The loser then waits on the role-name index
and failed with ``UniqueViolation`` on ``pg_authid_rolname_index`` (CI run 37830551379, job
113494518391). Deterministic here: session A creates the role and holds its transaction open;
session B runs the same statement, blocks on the index, and is released when A commits.

The statement is 0012's own upgrade SQL, read through a recorder ``op`` with only the role name
swapped for a unique one, so the real ``racket_media_worker`` and its grants are untouched.
Real Postgres.
"""

from __future__ import annotations

import importlib
import secrets
import threading
import time
from typing import Any

import psycopg
import pytest

pytestmark = pytest.mark.integration

ROLE = "racket_media_worker"


class _Op:
    def __init__(self) -> None:
        self.sql: list[str] = []

    def execute(self, statement: str) -> None:
        self.sql.append(str(statement))


def _create_role_sql(role: str, monkeypatch: pytest.MonkeyPatch) -> str:
    module = importlib.import_module("racket.migrations.versions.0012_media_worker_role")
    recorder = _Op()
    monkeypatch.setattr(module, "op", recorder)
    module.upgrade()
    [statement] = [s for s in recorder.sql if "CREATE ROLE" in s]
    return statement.replace(ROLE, role)


def _url(engine: Any) -> str:
    """A libpq URL for the session database (own connections, not the engine's pool)."""
    return str(engine.url.set(drivername="postgresql").render_as_string(hide_password=False))


def _waiting_on_lock(url: str, pid: int) -> bool:
    with psycopg.connect(url, autocommit=True, connect_timeout=5) as conn:
        row = conn.execute(
            "SELECT wait_event_type = 'Lock' FROM pg_stat_activity WHERE pid = %s", (pid,)
        ).fetchone()
        return bool(row and row[0])


def _role_count(url: str, role: str) -> int:
    with psycopg.connect(url, autocommit=True, connect_timeout=5) as conn:
        row = conn.execute("SELECT count(*) FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
        return int(row[0]) if row else 0


def _drop(url: str, role: str) -> None:
    with psycopg.connect(url, autocommit=True, connect_timeout=5) as conn:
        conn.execute(f"DROP ROLE IF EXISTS {role}")


def test_it_03_10c_a_second_migrator_racing_on_the_role_does_not_fail(
    db_engine: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = _url(db_engine)
    role = f"ra_it0310c_{secrets.token_hex(4)}"
    statement = _create_role_sql(role, monkeypatch)
    errors: list[BaseException] = []
    b_pid: list[int] = []

    def migrator_b() -> None:
        try:
            with psycopg.connect(url, connect_timeout=5) as conn:
                b_pid.append(conn.info.backend_pid)
                conn.execute(statement)
                conn.commit()
        except BaseException as exc:  # noqa: BLE001 - asserted below
            errors.append(exc)

    try:
        with psycopg.connect(url, connect_timeout=5) as a:
            a.execute(statement)  # A: role created, transaction still open
            b = threading.Thread(target=migrator_b)
            b.start()
            deadline = time.monotonic() + 10
            while not (b_pid and _waiting_on_lock(url, b_pid[0])):
                assert not errors, errors
                assert time.monotonic() < deadline, "B never reached the role-name index"
                time.sleep(0.05)
            a.commit()  # releases B into the collision
            b.join(timeout=10)
        assert not b.is_alive()
        assert errors == []
        assert _role_count(url, role) == 1
    finally:
        _drop(url, role)


def test_it_03_10c_the_role_is_still_created_when_absent(
    db_engine: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = _url(db_engine)
    role = f"ra_it0310c_{secrets.token_hex(4)}"
    statement = _create_role_sql(role, monkeypatch)
    try:
        with psycopg.connect(url, connect_timeout=5) as conn:
            conn.execute(statement)
            conn.commit()
        with psycopg.connect(url, autocommit=True, connect_timeout=5) as conn:
            row = conn.execute(
                "SELECT rolcanlogin, rolsuper FROM pg_roles WHERE rolname = %s", (role,)
            ).fetchone()
        assert row == (False, False)
    finally:
        _drop(url, role)
