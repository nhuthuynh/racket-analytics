"""Transaction-rollback database fixtures on a real Postgres (ST-004; AQS/OPS-05: never SQLite).

DATABASE_URL points at the Compose Postgres in CI, or at the throwaway cluster from
``scripts/dev-postgres.sh`` locally. Each test runs inside an outer transaction that is
rolled back, and the ORM session joins it with SAVEPOINTs, so code under test may call
``commit()`` freely and still leave nothing behind.
"""

from __future__ import annotations

import contextlib
import os
import re
import secrets
from collections.abc import Iterable, Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        pytest.fail(
            "DATABASE_URL is not set. Integration tests need a real Postgres: run "
            "`docker compose -f infra/compose.yaml up -d postgres` or "
            '`eval "$(scripts/dev-postgres.sh)"`. SQLite is not allowed (AQS/OPS-05).',
            pytrace=False,
        )
    parsed = make_url(url)
    if not parsed.drivername.startswith("postgresql"):
        pytest.fail(
            f"DATABASE_URL must be Postgres, got driver {parsed.drivername!r}", pytrace=False
        )
    if parsed.drivername == "postgresql":
        parsed = parsed.set(drivername="postgresql+psycopg")
    return parsed.render_as_string(hide_password=False)


def make_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True, future=True)


@contextmanager
def rolled_back_connection(engine: Engine) -> Iterator[Connection]:
    """A connection inside a transaction that is always rolled back."""
    connection = engine.connect()
    transaction = connection.begin()
    try:
        yield connection
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@contextmanager
def rolled_back_session(engine: Engine) -> Iterator[Session]:
    """An ORM session whose commits become SAVEPOINT releases inside a rolled-back transaction."""
    with rolled_back_connection(engine) as connection:
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()


# ----------------------------------------------------------------- one database per session
# C-32 (PE-R3-06), C-31 (PE-R2-04): `committed_db` truncates every table, so two pytest
# sessions on one database wipe each other's rows. Each session gets a fresh database next to
# the one DATABASE_URL names; DATABASE_URL is repointed so the app and every worker subprocess
# use it, and it is dropped at the end. RA_TEST_DB_ISOLATION=off keeps the shared database.
ISOLATION_ENV = "RA_TEST_DB_ISOLATION"
BASE_URL_ENV = "RA_TEST_BASE_DATABASE_URL"
_SESSION_DB = re.compile(r"^(?P<base>.+)_t(?P<pid>\d+)_[0-9a-f]{6}$")
_MAX_NAME = 63  # Postgres NAMEDATALEN - 1


def session_database_name(base: str, *, pid: int) -> str:
    suffix = f"_t{pid}_{secrets.token_hex(3)}"
    return base[: _MAX_NAME - len(suffix)] + suffix


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def stale_session_databases(names: Iterable[str]) -> set[str]:
    """Session databases whose creating process no longer exists on this host."""
    stale = set()
    for name in names:
        m = _SESSION_DB.match(name)
        if m and not _pid_alive(int(m["pid"])):
            stale.add(name)
    return stale


def _admin_engine(url: str) -> Engine:
    return create_engine(url, isolation_level="AUTOCOMMIT", pool_pre_ping=True, future=True)


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def create_session_database(base_url: str) -> str:
    """Create a fresh database beside ``base_url``'s and return its URL (same credentials).
    Databases left by dead sessions of the same base are dropped first (best effort)."""
    base = make_url(base_url)
    base_name = base.database or "postgres"
    engine = _admin_engine(base.render_as_string(hide_password=False))
    try:
        with engine.connect() as conn:
            names = conn.execute(
                text("SELECT datname FROM pg_database WHERE datname LIKE :p"),
                {"p": base_name.replace("_", "\\_") + "\\_t%"},
            ).scalars()
            for stale in sorted(stale_session_databases(names)):
                # another session may be dropping it too; a leftover is retried next time
                with contextlib.suppress(Exception):
                    conn.execute(text(f"DROP DATABASE IF EXISTS {_quote(stale)}"))
            name = session_database_name(base_name, pid=os.getpid())
            conn.execute(text(f"CREATE DATABASE {_quote(name)}"))
    finally:
        engine.dispose()
    return base.set(database=name).render_as_string(hide_password=False)


def drop_session_database(url: str, base_url: str) -> None:
    target = make_url(url)
    if not target.database or not _SESSION_DB.match(target.database):
        return  # never drop a database this module did not name
    engine = _admin_engine(make_url(base_url).render_as_string(hide_password=False))
    try:
        with engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {_quote(target.database)} WITH (FORCE)"))
    finally:
        engine.dispose()
