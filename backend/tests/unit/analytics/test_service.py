"""Analytics service rules that need no database (ST-046; invariant S8, analytics-snapshots.md
§3): a match the port reports gone gets no snapshot write."""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

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


# ---------------------------------------------------------------- read repair (S4, §4.2)
# Added test-first in the ST-046b port: a snapshot is recomputed only when it is missing or
# behind the live sheet, and the caller's session is committed either way (the lock ends).
OWNER = uuid.UUID("33333333-3333-4333-8333-333333333333")


class FakeRepo:
    stored: ClassVar[dict[Any, Any]] = {}
    writes: ClassVar[list[Any]] = []

    def __init__(self, session: Any) -> None:
        pass

    def get(self, key: Any) -> Any:
        return FakeRepo.stored.get(key)

    def upsert(self, snapshot: Any) -> bool:
        FakeRepo.writes.append(snapshot)
        FakeRepo.stored[snapshot.key] = snapshot
        return True


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    from racket.matches.public import LiveSheet
    from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game

    state: dict[str, Any] = {"version": 2, "match_id": uuid.uuid4()}
    sheet = one_game(WORKED_EXAMPLE)
    monkeypatch.setattr(
        service.matches,
        "lock_live_sheet",
        lambda session, match_id: LiveSheet(state["version"], OWNER, sheet),
    )
    FakeRepo.stored, FakeRepo.writes = {}, []
    monkeypatch.setattr(service, "SnapshotRepository", FakeRepo)
    return state


def _stored(match_id: uuid.UUID, version: int) -> Any:
    from racket.analytics.snapshot import MetricSnapshot
    from racket.sports.pickleball.metrics import load_dictionary
    from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game

    return MetricSnapshot.compute(
        match_id=match_id,
        owner_id=OWNER,
        sheet=one_game(WORKED_EXAMPLE),
        sheet_version=version,
        dictionary=load_dictionary(),
        now=service._now(),
    )


def test_a_current_snapshot_is_served_without_a_recompute(live: dict[str, Any]) -> None:
    snapshot = _stored(live["match_id"], 2)
    FakeRepo.stored[snapshot.key] = snapshot
    session = FakeSession()
    found = service.current(session, live["match_id"], trigger="read")  # type: ignore[arg-type]
    assert found is not None
    assert found.snapshot is snapshot
    assert FakeRepo.writes == []
    assert session.calls == ["commit"]


def test_a_snapshot_behind_the_live_sheet_is_recomputed_and_stored(
    live: dict[str, Any],
) -> None:
    old = _stored(live["match_id"], 1)
    FakeRepo.stored[old.key] = old
    session = FakeSession()
    found = service.current(session, live["match_id"], trigger="read")  # type: ignore[arg-type]
    assert found is not None
    assert found.sheet_version == 2
    assert [w.sheet_version for w in FakeRepo.writes] == [2]
    assert found.snapshot.sheet_version == 2
    assert session.calls == ["commit"]


def test_a_missing_snapshot_is_computed_and_stored(live: dict[str, Any]) -> None:
    session = FakeSession()
    found = service.current(session, live["match_id"], trigger="event")  # type: ignore[arg-type]
    assert found is not None
    assert [w.sheet_version for w in FakeRepo.writes] == [2]
    assert session.calls == ["commit"]
