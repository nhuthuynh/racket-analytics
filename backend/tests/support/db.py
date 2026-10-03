"""Transaction-rollback database fixtures on a real Postgres (ST-004; AQS/OPS-05: never SQLite).

DATABASE_URL points at the Compose Postgres in CI, or at the throwaway cluster from
``scripts/dev-postgres.sh`` locally. Each test runs inside an outer transaction that is
rolled back, and the ORM session joins it with SAVEPOINTs, so code under test may call
``commit()`` freely and still leave nothing behind.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import Connection, Engine, create_engine
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
