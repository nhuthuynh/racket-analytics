"""BE-PL-01: a migration that fails half-way leaves nothing behind. ``upgrade_to_head`` used to
commit in ``finally`` after the unlock, so the DDL that ran before the failing statement was
committed while ``alembic_version`` stayed behind. No I/O: the engine is a recorder."""

from __future__ import annotations

from typing import Any

import pytest

from racket.platform import db

pytestmark = pytest.mark.unit


class _Conn:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def __enter__(self) -> _Conn:
        return self

    def __exit__(self, *exc: object) -> None:
        self.calls.append("close")

    def execute(self, statement: Any, params: Any = None) -> None:
        text = str(statement)
        self.calls.append("unlock" if "unlock" in text else "lock" if "lock" in text else text)

    def commit(self) -> None:
        self.calls.append("commit")

    def rollback(self) -> None:
        self.calls.append("rollback")


class _Engine:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def connect(self) -> _Conn:
        return _Conn(self.calls)

    def dispose(self) -> None:
        self.calls.append("dispose")


def test_a_failing_migration_is_rolled_back_before_anything_is_committed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(db, "create_engine", lambda url: _Engine(calls))

    def failing_upgrade(config: Any, revision: str) -> None:
        calls.append("upgrade")
        raise RuntimeError("third statement failed")

    monkeypatch.setattr(db.command, "upgrade", failing_upgrade)
    with pytest.raises(RuntimeError):
        db.upgrade_to_head("postgresql://u:p@h/d")
    assert calls.index("rollback") < calls.index("unlock")
    assert "commit" not in calls[: calls.index("rollback")]


def test_a_successful_migration_is_committed_and_unlocked(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(db, "create_engine", lambda url: _Engine(calls))
    monkeypatch.setattr(db.command, "upgrade", lambda config, revision: calls.append("upgrade"))
    db.upgrade_to_head("postgresql://u:p@h/d")
    assert calls[:3] == ["lock", "upgrade", "commit"]
    assert "rollback" not in calls
    assert "unlock" in calls
