"""``DELETE /me`` as one transaction under the account row lock (ST-051; FR-007; NFR-057;
deletion-and-purge.md §3.2, §3.3). No I/O: the ports of Matches and Identity & Players are
replaced by recorders, so the order of the steps and the "nothing written on a refusal" rule are
read directly. Negative cases first. The real-database behaviour is IT-03-08 and
``tests/integration/test_st_051_account_purged_last.py``.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import Any

import pytest

from racket.matches import service as match_service_module
from racket.matches.domain import OwnerId
from racket.matches.service import MatchService
from racket.platform.errors import Unauthenticated, ValidationFailed
from racket.players import service as service_module
from racket.players.service import AccountDeletion

pytestmark = [pytest.mark.unit]

NOW = dt.datetime(2026, 10, 9, 12, 0, tzinfo=dt.UTC)
ME = uuid.UUID("00000000-0000-4000-8000-0000000000a1")
MATCHES = [uuid.UUID(f"00000000-0000-4000-8000-00000000000{i}") for i in (1, 2)]
CONFIRMED = {"confirm": "delete"}


class _Calls(list[str]):
    """The steps in the order they ran; ``live`` is what the account lock finds."""

    live = True


class _Session:
    """Stands in for the ORM session; records ``commit`` / ``rollback`` only."""

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def commit(self) -> None:
        self.calls.append("commit")

    def rollback(self) -> None:
        self.calls.append("rollback")


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> _Calls:
    recorded = _Calls()

    def lock_for_deletion(session: Any, account_id: uuid.UUID) -> bool:
        recorded.append("lock_for_deletion")
        return recorded.live

    def tombstone_owned_by(session: Any, owner_id: uuid.UUID, at: dt.datetime) -> list[uuid.UUID]:
        assert (owner_id, at) == (ME, NOW)
        recorded.append("tombstone_owned_by")
        return list(MATCHES)

    def erase_and_sign_out(session: Any, account_id: uuid.UUID, at: dt.datetime) -> None:
        assert (account_id, at) == (ME, NOW)
        recorded.append("erase_and_sign_out")

    monkeypatch.setattr(service_module.players, "lock_for_deletion", lock_for_deletion)
    monkeypatch.setattr(service_module.players, "erase_and_sign_out", erase_and_sign_out)
    monkeypatch.setattr(service_module.matches, "tombstone_owned_by", tombstone_owned_by)
    return recorded


def _delete(calls: list[str], body: object) -> Any:
    return AccountDeletion(_Session(calls), clock=lambda: NOW).delete(ME, body)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "body", [None, {}, {"confirm": "DELETE"}, {"confirm": "delete", "extra": 1}, "delete"]
)
def test_without_the_typed_confirmation_nothing_is_locked_or_written(
    calls: list[str], body: object
) -> None:
    with pytest.raises(ValidationFailed):
        _delete(calls, body)
    assert calls == ["rollback"]


def test_an_account_already_deleted_is_401_and_nothing_is_written(calls: _Calls) -> None:
    calls.live = False
    with pytest.raises(Unauthenticated):
        _delete(calls, CONFIRMED)
    assert calls == ["lock_for_deletion", "rollback"]


def test_a_failure_after_the_lock_rolls_everything_back(
    calls: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(session: Any, account_id: uuid.UUID, at: dt.datetime) -> None:
        calls.append("erase_and_sign_out")
        raise RuntimeError("injected")

    monkeypatch.setattr(service_module.players, "erase_and_sign_out", broken)
    with pytest.raises(RuntimeError):
        _delete(calls, CONFIRMED)
    assert calls == ["lock_for_deletion", "tombstone_owned_by", "erase_and_sign_out", "rollback"]


def test_the_lock_comes_first_then_the_matches_then_the_address_then_one_commit(
    calls: list[str],
) -> None:
    tombstone = _delete(calls, CONFIRMED)
    assert calls == ["lock_for_deletion", "tombstone_owned_by", "erase_and_sign_out", "commit"]
    assert tombstone.deleted_at == NOW
    assert tombstone.response() == {"deleted": True, "purge_due_by": "2026-10-16T12:00:00Z"}


def test_the_log_lines_carry_ids_only(calls: list[str], caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="racket.players.service"):
        _delete(calls, CONFIRMED)
    lines = [r for r in caplog.records if r.name == "racket.players.service"]
    events = [(getattr(r, "event", None), getattr(r, "match_id", None)) for r in lines]
    assert events == [
        ("match.deleted", str(MATCHES[0])),
        ("match.deleted", str(MATCHES[1])),
        ("account.deleted", None),
    ]
    assert all(getattr(r, "user_id", None) == str(ME) for r in lines)
    for record in lines:
        assert set(vars(record)) & {"email", "email_key", "username", "display_name"} == set()


# ------------------------------------------------- SEC-S3-TM-05: creation needs a live account
class _MatchSession(_Session):
    def add(self, _: object) -> None:  # pragma: no cover - an add here would be a defect
        self.calls.append("add")


def test_a_deleted_account_cannot_create_a_match(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def lock_live_account(session: Any, account_id: uuid.UUID) -> bool:
        calls.append("lock_live_account")
        return False

    def add(self: Any, match: Any) -> None:  # pragma: no cover - a write here is the defect
        calls.append("add")

    monkeypatch.setattr(match_service_module.players, "lock_live_account", lock_live_account)
    monkeypatch.setattr(match_service_module.MatchRepository, "add", add)
    service = MatchService(_MatchSession(calls))  # type: ignore[arg-type]
    with pytest.raises(Unauthenticated):
        service.create(OwnerId(ME), {"format": "doubles"}, today=NOW.date())
    assert calls == ["lock_live_account", "rollback"]


def test_a_live_account_creates_its_match_under_the_account_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def lock_live_account(session: Any, account_id: uuid.UUID) -> bool:
        calls.append("lock_live_account")
        return True

    def add(self: Any, match: Any) -> None:
        calls.append("add")

    monkeypatch.setattr(match_service_module.players, "lock_live_account", lock_live_account)
    monkeypatch.setattr(match_service_module.MatchRepository, "add", add)
    service = MatchService(_MatchSession(calls))  # type: ignore[arg-type]
    service.create(OwnerId(ME), {"format": "doubles"}, today=NOW.date())
    assert calls == ["lock_live_account", "add", "commit"]
