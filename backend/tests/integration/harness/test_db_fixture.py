"""Self-test of the transaction-rollback DB fixtures on a real Postgres (ST-004)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text

from tests.support.db import rolled_back_connection, rolled_back_session


def _table_exists(engine: Any, name: str) -> bool:
    with engine.connect() as conn:
        return bool(conn.execute(text("SELECT to_regclass(:n) IS NOT NULL"), {"n": name}).scalar())


def test_connection_fixture_rolls_back_ddl_and_rows(raw_db_engine: Any) -> None:
    table = f"harness_{uuid.uuid4().hex[:8]}"
    with rolled_back_connection(raw_db_engine) as conn:
        conn.execute(text(f"CREATE TABLE {table} (id int)"))
        conn.execute(text(f"INSERT INTO {table} VALUES (1)"))
        assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar() == 1

    assert not _table_exists(raw_db_engine, table)


def test_session_commit_inside_the_fixture_is_still_rolled_back(raw_db_engine: Any) -> None:
    table = f"harness_{uuid.uuid4().hex[:8]}"
    with raw_db_engine.begin() as conn:
        conn.execute(text(f"CREATE TABLE {table} (id int)"))
    try:
        with rolled_back_session(raw_db_engine) as session:
            session.execute(text(f"INSERT INTO {table} VALUES (1)"))
            session.commit()  # code under test may commit
            assert session.execute(text(f"SELECT count(*) FROM {table}")).scalar() == 1

        with raw_db_engine.connect() as conn:
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar() == 0
    finally:
        with raw_db_engine.begin() as conn:
            conn.execute(text(f"DROP TABLE {table}"))


def test_uncommitted_work_is_invisible_to_other_connections(raw_db_engine: Any) -> None:
    table = f"harness_{uuid.uuid4().hex[:8]}"
    with rolled_back_connection(raw_db_engine) as conn:
        conn.execute(text(f"CREATE TABLE {table} (id int)"))
        assert not _table_exists(raw_db_engine, table)
