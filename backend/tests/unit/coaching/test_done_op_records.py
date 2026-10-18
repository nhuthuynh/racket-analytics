"""ST-062 review PE-062-R1-01/02 (threat-notes-sprint-04 T4-PL-3, T4-PL-5; api-sprint-04 §3.1):
which ``POST .../done`` ops ``PlanService`` records, over an in-memory plan store.

A new key on an already-done session is a no-op and stores no record (T4-PL-5: one record per
mark at most, so a client looping new keys cannot grow ``plan_done_ops``); the record is keyed by
the account (T4-PL-3). Negative case first.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from racket.coaching import service as svc
from racket.coaching.plan.domain import TrainingPlan
from racket.coaching.plan.repository import DoneOp, StoredPlan, StoredSession
from tests.unit.coaching.test_plan_follow_through import plan

pytestmark = pytest.mark.unit

AT = datetime(2026, 10, 18, 9, 30, tzinfo=UTC)
IVY, CARLOS = uuid.UUID(int=1), uuid.UUID(int=2)


class FakeDb:
    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class FakePlans:
    """The owner's one plan and the done ops, keyed as ``plan_done_ops`` is."""

    def __init__(self, owner_id: uuid.UUID, p: TrainingPlan) -> None:
        self.stored = StoredPlan(
            uuid.uuid4(),
            owner_id,
            False,
            p,
            sessions=tuple(StoredSession(uuid.uuid4(), None, ()) for _ in p.sessions),
        )
        self.ops: dict[tuple[uuid.UUID, str], DoneOp] = {}

    def get(self, owner_id: uuid.UUID) -> StoredPlan | None:
        return self.stored if owner_id == self.stored.owner_id else None

    def update(self, *_: Any, **__: Any) -> None:
        pass

    def done_op(self, owner_id: uuid.UUID, op_id: str) -> DoneOp | None:
        return self.ops.get((owner_id, op_id))

    def record_done_op(self, owner_id: uuid.UUID, op_id: str, result: DoneOp) -> None:
        assert (owner_id, op_id) not in self.ops
        self.ops[(owner_id, op_id)] = result


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> svc.PlanService:
    monkeypatch.setattr(svc.players, "lock_live_account", lambda _db, _owner: True)
    s = svc.PlanService(FakeDb(), svc.Library((), {}, "sha256:test"), clock=lambda: AT)  # type: ignore[arg-type]
    s.plans = FakePlans(IVY, plan())  # type: ignore[assignment]
    return s


def _plans(s: svc.PlanService) -> FakePlans:
    plans = s.plans
    assert isinstance(plans, FakePlans)
    return plans


def test_a_second_key_on_a_done_session_writes_no_row(service: svc.PlanService) -> None:
    session_id = _plans(service).stored.sessions[0].id
    first = service.mark_done(IVY, session_id, "op-a")
    again = service.mark_done(IVY, session_id, "op-b")
    assert again == first  # a no-op: same done_at and version, not replayed
    assert set(_plans(service).ops) == {(IVY, "op-a")}
    # op-b stored nothing, so sending it again is the same no-op, not a replay
    assert service.mark_done(IVY, session_id, "op-b") == first


def test_the_op_record_is_keyed_by_the_account(service: svc.PlanService) -> None:
    session_id = _plans(service).stored.sessions[1].id
    done = service.mark_done(IVY, session_id, "op-k")
    assert _plans(service).ops == {(IVY, "op-k"): DoneOp(session_id, done.plan_version, AT)}
    assert _plans(service).done_op(CARLOS, "op-k") is None
