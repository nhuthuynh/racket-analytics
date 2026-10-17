"""The account purge removes the account's training-plan rows before the account row (ST-061a;
ADR 0042 order; coaching-plan §8; deletion-and-purge.md §4.2). Each context's port is faked;
the live check is IT-04-02c.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from racket.platform import purge

pytestmark = [pytest.mark.unit]

ACCOUNT = uuid.UUID(int=7)
SESSION = object()


def _record(calls: list[str], name: str) -> Any:
    def port(session: Any, account_id: uuid.UUID) -> int:
        assert (session, account_id) == (SESSION, ACCOUNT)
        calls.append(name)
        return 0

    return port


def test_a_failed_plan_purge_leaves_the_account_row(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def failing(session: Any, account_id: uuid.UUID) -> int:
        calls.append("coaching")
        raise RuntimeError("plan rows not deleted")

    monkeypatch.setattr("racket.coaching.public.purge_account", failing)
    monkeypatch.setattr("racket.players.public.purge_account", _record(calls, "players"))
    with pytest.raises(RuntimeError):
        purge.ContextPorts().purge_account(SESSION, ACCOUNT)
    assert calls == ["coaching"]


def test_plan_rows_go_before_the_account_row(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr("racket.coaching.public.purge_account", _record(calls, "coaching"))
    monkeypatch.setattr("racket.players.public.purge_account", _record(calls, "players"))
    purge.ContextPorts().purge_account(SESSION, ACCOUNT)
    assert calls == ["coaching", "players"]
