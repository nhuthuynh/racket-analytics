"""Steps for tests/features/media_worker_identity.feature (ST-042; NFR-054; SEC-R1S3-01).

Each step runs one statement inside a transaction with ``SET LOCAL ROLE racket_media_worker``
(the group role the Compose worker login belongs to) and rolls it back. Real Postgres.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from pytest_bdd import given, parsers, scenarios, then, when
from sqlalchemy.exc import ProgrammingError

scenarios("media_worker_identity.feature")

WORKER_ROLE = "racket_media_worker"
_IDENTIFIER = frozenset("abcdefghijklmnopqrstuvwxyz_")


def _identifier(name: str) -> str:
    assert name, "empty identifier"
    assert set(name) <= _IDENTIFIER, f"not a plain identifier: {name!r}"
    return name


def _as_worker(engine: Any, statement: str) -> BaseException | None:
    with engine.connect() as conn:
        tx = conn.begin()
        try:
            conn.execute(sa.text(f"SET LOCAL ROLE {WORKER_ROLE}"))
            conn.execute(sa.text(statement))
        except ProgrammingError as exc:
            return exc
        finally:
            tx.rollback()
    return None


@given("the database is migrated", target_fixture="engine")
def migrated(db_engine: Any) -> Any:
    return db_engine


@when(parsers.parse("the media worker role reads the {table} table"), target_fixture="outcome")
def worker_reads(engine: Any, table: str) -> BaseException | None:
    return _as_worker(engine, f"SELECT count(*) FROM {_identifier(table)}")


@when(parsers.parse("the media worker role updates {column} of {table}"), target_fixture="outcome")
def worker_updates(engine: Any, column: str, table: str) -> BaseException | None:
    column, table = _identifier(column), _identifier(table)
    return _as_worker(engine, f"UPDATE {table} SET {column} = {column} WHERE false")


@then(parsers.parse('the database answers "{message}"'))
def refused(outcome: BaseException | None, message: str) -> None:
    assert outcome is not None, "the statement was allowed"
    assert message in str(outcome)


@then("the read succeeds")
@then("the update succeeds")
def allowed(outcome: BaseException | None) -> None:
    assert outcome is None, f"the statement was refused: {outcome}"
