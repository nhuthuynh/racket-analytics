"""Roles are keyed by account id, never by address (C4-TAC5; T-AC-5; SEC-S3-TM-07; ADR 0045;
threat-model-sprint-03 T-AC-5). Identity & Players grants and reads the labeller role only
through its published port (``racket.players.public``); a re-created account has a new id, so
it holds no role. No I/O: the session records the statements, which are compiled for Postgres
and read. Negative cases first. The real-database behaviour is IT-04-12 in
``tests/integration/test_it_03_08_delete_account.py``.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

import pytest
from sqlalchemy.dialects import postgresql

from racket.players import public
from racket.players.models import account_roles

pytestmark = [pytest.mark.unit]

NOW = dt.datetime(2026, 10, 17, 9, 0, tzinfo=dt.UTC)
OLD = uuid.UUID("00000000-0000-4000-8000-0000000000a1")
NEW = uuid.UUID("00000000-0000-4000-8000-0000000000b2")


class _Result:
    def __init__(self, row: object) -> None:
        self.row = row

    def first(self) -> object:
        return self.row


class _Session:
    """Stands in for the ORM session: records every statement, finds ``row`` for each."""

    def __init__(self, row: object = None) -> None:
        self.statements: list[Any] = []
        self.row = row

    def execute(self, statement: Any) -> _Result:
        self.statements.append(statement)
        return _Result(self.row)


def _sql(statement: Any) -> tuple[str, dict[str, Any]]:
    dialect: Any = postgresql.dialect
    compiled = statement.compile(dialect=dialect())
    return str(compiled), dict(compiled.params)


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> list[uuid.UUID]:
    """``lock_live_account`` finds the ids in the returned list (the live accounts)."""
    alive: list[uuid.UUID] = []
    monkeypatch.setattr(public, "lock_live_account", lambda _session, a_id: a_id in alive)
    return alive


def test_an_unknown_role_is_not_granted_and_nothing_is_written(live: list[uuid.UUID]) -> None:
    live.append(NEW)
    session = _Session()
    assert public.grant_role(session, NEW, "admin", NOW) is False  # type: ignore[arg-type]
    assert session.statements == []


def test_a_deleted_account_is_not_granted_a_role(live: list[uuid.UUID]) -> None:
    session = _Session()
    assert public.grant_role(session, OLD, "labeller", NOW) is False  # type: ignore[arg-type]
    assert session.statements == []


def test_a_grant_writes_one_row_keyed_by_that_account_id_only(live: list[uuid.UUID]) -> None:
    live.append(NEW)
    session = _Session()
    assert public.grant_role(session, NEW, "labeller", NOW) is True  # type: ignore[arg-type]
    assert len(session.statements) == 1
    sql, params = _sql(session.statements[0])
    assert sql.startswith("INSERT INTO account_roles")
    assert params == {"account_id": NEW, "role": "labeller", "granted_at": NOW}


def test_the_role_table_holds_no_address_or_name() -> None:
    """T-AC-5 mitigation: "The role is never keyed by address". A role row names an account id,
    a role and a time; nothing that survives into a new account with the same address."""
    assert {c.name for c in account_roles.columns} == {"account_id", "role", "granted_at"}
    assert {c.name for c in account_roles.primary_key.columns} == {"account_id", "role"}


def test_has_role_asks_for_that_account_id_and_a_live_account() -> None:
    session = _Session(row=None)
    assert public.has_role(session, NEW, "labeller") is False  # type: ignore[arg-type]
    (statement,) = session.statements
    sql, params = _sql(statement)
    assert "account_roles.account_id = %(account_id_1)s" in sql
    assert params["account_id_1"] == NEW
    assert "accounts.deleted_at IS NULL" in sql
    assert "email" not in sql, "a role is never found by address"
    assert "username" not in sql, "a role is never found by name"


def test_has_role_is_true_only_when_a_row_is_found() -> None:
    assert public.has_role(_Session(row=("labeller",)), NEW, "labeller") is True  # type: ignore[arg-type]
    assert public.has_role(_Session(row=None), NEW, "labeller") is False  # type: ignore[arg-type]


def test_the_only_role_is_the_labeller_role() -> None:
    assert frozenset({"labeller"}) == public.ROLES
