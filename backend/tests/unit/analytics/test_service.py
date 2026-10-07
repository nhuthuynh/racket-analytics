"""Analytics service rules that need no database (ST-046; invariant S8, analytics-snapshots.md
§3): a match the port reports gone gets no snapshot write."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from racket.analytics import service

pytestmark = [pytest.mark.unit]


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append("execute")
        raise AssertionError("no statement may run for a gone match")

    def rollback(self) -> None:
        self.calls.append("rollback")

    def commit(self) -> None:
        self.calls.append("commit")


def test_a_gone_match_writes_no_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service.matches, "lock_live_sheet", lambda session, match_id: None)
    session = FakeSession()
    assert service.current(session, uuid.uuid4(), trigger="event") is None  # type: ignore[arg-type]
    assert session.calls == ["rollback"]
