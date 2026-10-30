"""QA-VERIFY04R3-07 (G04-11 c): the statements ``PlanRepository`` sends (ST-061a, ST-062;
coaching-plan §1, §5, §8, §9; T4-PL-3, T4-PL-9).

The repository's rules are in its statements: every read and write of a plan row filters by the
owner, ``update`` is an optimistic write on the loaded version (0 rows -> ``PlanConflict``), a
purge marks citing plans stale and deletes every row naming the match, and ``get`` rebuilds the
aggregate and the session/assignment ids in plan order. A recording session stands in for
Postgres (unit level: no I/O); each statement is compiled with the Postgres dialect and its WHERE
clause and values are checked. IT-04-02 / IT-04-05 / IT-04-07 run the same code on Postgres.
Negative cases first.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.dialects import postgresql

from racket.coaching.plan import repository as repo
from racket.coaching.plan.repository import DoneOp, PlanConflict, PlanRepository
from tests.unit.coaching.test_plan_follow_through import DRIVES, LIB, plan

pytestmark = [pytest.mark.unit, pytest.mark.coaching]

IVY, PLAN, M1, M2, S1 = (uuid.UUID(int=n) for n in (1, 2, 11, 12, 21))
NAMES = {str(IVY): "IVY", str(PLAN): "PLAN", str(M1): "M1", str(M2): "M2", str(S1): "S1"}
AT = datetime(2026, 10, 18, 9, 30, tzinfo=UTC)
LATER = datetime(2026, 10, 19, 7, 0, tzinfo=UTC)
PG = postgresql.dialect()  # type: ignore[no-untyped-call]


class Row:
    """A result row: attribute access and ``_mapping``, as SQLAlchemy's ``Row``."""

    def __init__(self, **values: Any) -> None:
        self._mapping = values

    def __getattr__(self, name: str) -> Any:
        try:
            return self._mapping[name]
        except KeyError:
            raise AttributeError(name) from None


class Result:
    def __init__(self, rows: list[Any] | None = None, rowcount: int = 1) -> None:
        self.rows, self.rowcount = rows or [], rowcount

    def one_or_none(self) -> Any:
        assert len(self.rows) <= 1
        return self.rows[0] if self.rows else None

    def all(self) -> list[Any]:
        return list(self.rows)

    def scalars(self) -> Iterator[Any]:
        return iter(self.rows)

    def __iter__(self) -> Iterator[Any]:
        return iter(self.rows)


class RecordingDb:
    """Answers each statement with the next queued ``Result`` (default: 1 row affected)."""

    def __init__(self, *answers: Result) -> None:
        self.answers = list(answers)
        self.sent: list[tuple[Any, Any]] = []

    def execute(self, statement: Any, params: Any = None) -> Result:
        self.sent.append((statement, params))
        return self.answers.pop(0) if self.answers else Result()


def where(statement: Any) -> str:
    """The WHERE clause as Postgres SQL with literal values, known ids by name."""
    text = str(statement.whereclause.compile(dialect=PG, compile_kwargs={"literal_binds": True}))
    text = " ".join(text.split())
    return re.sub(r"'([0-9a-f-]{36})'", lambda m: NAMES.get(m.group(1), m.group(1)), text)


def values(statement: Any) -> dict[str, Any]:
    """The SET / VALUES of an UPDATE or INSERT (WHERE parameters end in ``_<n>``)."""
    params = statement.compile(dialect=PG).params
    return {k: v for k, v in params.items() if not re.search(r"_\d+$", k)}


def selected(statement: Any) -> list[str]:
    """The columns a SELECT reads, as ``table.column``."""
    return [f"{c.table.name}.{c.name}" for c in statement.selected_columns]


def every_column(table: Any) -> list[str]:
    return [f"{table.name}.{c.name}" for c in table.columns]


def kind(statement: Any) -> tuple[str, str]:
    return type(statement).__name__, statement.table.name


def ids() -> Iterator[uuid.UUID]:
    return (uuid.UUID(int=1000 + n) for n in range(1000))


def stored_rows() -> repo.PlanRows:
    rows = repo.to_rows(plan(), plan_id=PLAN, owner_id=IVY, new_id=ids().__next__)
    rows.sessions[4]["done_at"] = AT  # week 2 session 2
    return rows


# ------------------------------------------------------------------ get
def test_get_of_an_owner_with_no_plan_reads_only_the_owner_s_root() -> None:
    db = RecordingDb(Result([]))
    assert PlanRepository(db, LIB.values()).get(IVY) is None  # type: ignore[arg-type]
    [(statement, _)] = db.sent
    assert where(statement) == "training_plans.owner_id = IVY"


def test_get_rebuilds_the_plan_and_its_ids_in_plan_order() -> None:
    rows = stored_rows()
    root = Row(**rows.plan, created_at=AT, updated_at=AT)
    db = RecordingDb(
        Result([root]),
        Result([Row(**s) for s in reversed(rows.sessions)]),
        Result([Row(**a) for a in reversed(rows.assignments)]),
        Result([str(M2), str(M1)]),
    )
    stored = PlanRepository(db, LIB.values()).get(IVY)  # type: ignore[arg-type]
    assert stored is not None
    assert (stored.id, stored.owner_id, stored.stale, stored.created_at) == (PLAN, IVY, False, AT)
    assert stored.plan.content() == plan().content()
    assert stored.source_match_ids == frozenset({M1, M2})
    assert [s.id for s in stored.sessions] == [s["id"] for s in rows.sessions]
    assert [s.done_at for s in stored.sessions] == [None, None, None, None, AT, None]
    by_session = [
        [a["id"] for a in rows.assignments if a["session_id"] == s.id] for s in stored.sessions
    ]
    assert [list(s.assignment_ids) for s in stored.sessions] == by_session
    assert stored.plan.sessions[4].done_at == AT
    session_ids = ", ".join(str(s["id"]) for s in reversed(rows.sessions))
    assert [where(s) for s, _ in db.sent] == [
        "training_plans.owner_id = IVY",
        "plan_sessions.owner_id = IVY AND plan_sessions.plan_id = PLAN",
        f"plan_assignments.owner_id = IVY AND plan_assignments.session_id IN ({session_ids})",
        "plan_source_matches.plan_id = PLAN",
    ]
    assert [selected(s) for s, _ in db.sent] == [
        every_column(repo.training_plans),
        every_column(repo.plan_sessions),
        every_column(repo.plan_assignments),
        ["plan_source_matches.match_id"],
    ]


# ------------------------------------------------------------------ delete, purge
def test_delete_owned_removes_only_the_owner_s_rows_and_counts_them() -> None:
    db = RecordingDb(*(Result(rowcount=n) for n in (1, 2, 9, 6, 1)))
    assert PlanRepository(db, ()).delete_owned(IVY) == 19  # type: ignore[arg-type]
    assert [(kind(s), where(s)) for s, _ in db.sent] == [
        (("Delete", "plan_done_ops"), "plan_done_ops.account_id = IVY"),
        (
            ("Delete", "plan_source_matches"),
            "plan_source_matches.plan_id IN (SELECT training_plans.id FROM training_plans "
            "WHERE training_plans.owner_id = IVY)",
        ),
        (("Delete", "plan_assignments"), "plan_assignments.owner_id = IVY"),
        (("Delete", "plan_sessions"), "plan_sessions.owner_id = IVY"),
        (("Delete", "training_plans"), "training_plans.owner_id = IVY"),
    ]


def test_purge_match_marks_citing_plans_stale_and_deletes_every_row_naming_it() -> None:
    db = RecordingDb(Result(rowcount=3), Result(rowcount=4), Result(rowcount=2))
    assert repo.purge_match(db, M1) == 6  # type: ignore[arg-type]  # rows deleted, not marked
    (stale, _), (rallies, _), (sources, _) = db.sent
    assert kind(stale) == ("Update", "training_plans")
    assert values(stale) == {"stale": True}
    assert where(stale) == (
        "training_plans.id IN (SELECT plan_source_matches.plan_id FROM plan_source_matches "
        "WHERE plan_source_matches.match_id = M1)"
    )
    assert (kind(rallies), where(rallies)) == (
        ("Delete", "plan_citation_rallies"),
        "plan_citation_rallies.match_id = M1",
    )
    assert (kind(sources), where(sources)) == (
        ("Delete", "plan_source_matches"),
        "plan_source_matches.match_id = M1",
    )


# ------------------------------------------------------------------ save
def test_save_without_source_matches_writes_no_source_row() -> None:
    db = RecordingDb()
    PlanRepository(db, LIB.values(), clock=lambda: AT).save(IVY, plan())  # type: ignore[arg-type]
    assert [kind(s)[1] for s, _ in db.sent[5:]] == [
        "training_plans",
        "plan_sessions",
        "plan_assignments",
    ]


def test_save_replaces_the_owner_s_plan_with_its_rows_and_sources() -> None:
    db = RecordingDb()
    p = plan()
    plan_id = PlanRepository(db, LIB.values(), clock=lambda: AT).save(  # type: ignore[arg-type]
        IVY, p, [M2, M1, M2]
    )
    assert [kind(s)[0] for s, _ in db.sent[:5]] == ["Delete"] * 5  # delete_owned first
    assert where(db.sent[0][0]) == "plan_done_ops.account_id = IVY"
    assert isinstance(plan_id, uuid.UUID)
    (root, _), (sessions, s_rows), (assignments, a_rows), (sources, src_rows) = db.sent[5:]
    assert kind(root) == ("Insert", "training_plans")
    stored = values(root)
    assert stored["id"] == plan_id
    assert (stored["owner_id"], stored["version"], stored["created_at"], stored["updated_at"]) == (
        IVY,
        1,
        AT,
        AT,
    )
    assert (stored["limited_data"], stored["stale"]) == (False, False)
    assert stored["content_digest"] == p.content_digest()
    assert kind(sessions) == ("Insert", "plan_sessions")
    assert [(r["plan_id"], r["owner_id"], r["week"], r["session_index"]) for r in s_rows] == [
        (plan_id, IVY, w, i) for w in (1, 2) for i in (1, 2, 3)
    ]
    assert kind(assignments) == ("Insert", "plan_assignments")
    assert len(a_rows) == 18
    assert {r["owner_id"] for r in a_rows} == {IVY}
    assert kind(sources) == ("Insert", "plan_source_matches")
    assert src_rows == [{"plan_id": plan_id, "match_id": M1}, {"plan_id": plan_id, "match_id": M2}]


def test_the_default_clock_is_utc() -> None:
    db = RecordingDb()
    PlanRepository(db, LIB.values()).save(IVY, plan())  # type: ignore[arg-type]
    created = values(db.sent[5][0])["created_at"]
    assert created.tzinfo is UTC


# ------------------------------------------------------------------ update
def test_update_of_a_changed_or_foreign_plan_is_a_conflict_and_writes_nothing_else() -> None:
    db = RecordingDb(Result(rowcount=0))
    repository = PlanRepository(db, LIB.values(), clock=lambda: LATER)  # type: ignore[arg-type]
    with pytest.raises(PlanConflict, match=str(PLAN)):
        repository.update(IVY, PLAN, plan(), loaded_version=3)
    [(statement, _)] = db.sent
    assert where(statement) == (
        "training_plans.id = PLAN AND training_plans.owner_id = IVY AND training_plans.version = 3"
    )


def _slots(rows: repo.PlanRows) -> Result:
    return Result([Row(**s) for s in rows.sessions])


def test_an_assignment_slot_that_is_not_stored_is_refused() -> None:
    rows = stored_rows()
    db = RecordingDb(Result(), _slots(rows), Result(), Result(rowcount=0))
    with pytest.raises(ValueError, match=f"plan {PLAN} has no slot 1.1.1"):
        PlanRepository(db, LIB.values()).update(IVY, PLAN, plan(), loaded_version=1)  # type: ignore[arg-type]


def test_update_writes_the_new_version_done_state_and_drills_into_the_stored_slots() -> None:
    rows = stored_rows()
    p = plan()
    p.mark_done(week=1, index=2, at=AT)
    p.swap(week=1, index=1, position=2, library=[DRIVES], cited={"AN-04"}, reason="too hard")
    db = RecordingDb(Result(), _slots(rows))
    PlanRepository(db, LIB.values(), clock=lambda: LATER).update(  # type: ignore[arg-type]
        IVY, PLAN, p, loaded_version=1
    )
    (root, _), (slots, _), *writes = db.sent
    assert values(root) == {
        "version": 3,
        "content_digest": p.content_digest(),
        "excluded_drills": ["pb.test.wall-dinks@1"],
        "updated_at": LATER,
    }
    assert where(slots) == "plan_sessions.owner_id = IVY AND plan_sessions.plan_id = PLAN"
    assert selected(slots) == every_column(repo.plan_sessions)
    assert len(writes) == 6 * (1 + 3)
    session_writes = writes[0::4]
    slot_ids = [str(s["id"]) for s in rows.sessions]
    assert [where(s) for s, _ in session_writes] == [
        f"plan_sessions.owner_id = IVY AND plan_sessions.id = {sid}" for sid in slot_ids
    ]
    assert [values(s)["done_at"] for s, _ in session_writes] == [None, AT, None, None, None, None]
    swapped, _ = writes[2]
    assert where(swapped) == (
        f"plan_assignments.owner_id = IVY AND plan_assignments.session_id = {slot_ids[0]} "
        "AND plan_assignments.position = 2"
    )
    assert values(swapped) == {
        "drill_ref": "pb.test.a-wall-drives@1",
        "minutes": 12,
        "weakness_id": "unforced_errors",
        "reason_not_for_me": "too hard",
    }


# ------------------------------------------------------------------ done ops
def test_an_unknown_done_op_is_none_and_is_looked_up_by_account_and_key() -> None:
    db = RecordingDb(Result([]))
    assert PlanRepository(db, ()).done_op(IVY, "op-a") is None  # type: ignore[arg-type]
    assert where(db.sent[0][0]) == "plan_done_ops.account_id = IVY AND plan_done_ops.op_id = 'op-a'"
    assert selected(db.sent[0][0]) == every_column(repo.plan_done_ops)


def test_a_recorded_done_op_answers_with_its_session_version_and_time() -> None:
    db = RecordingDb(Result([Row(session_id=S1, plan_version=4, created_at=AT)]))
    assert PlanRepository(db, ()).done_op(IVY, "op-a") == DoneOp(S1, 4, AT)  # type: ignore[arg-type]


def test_record_done_op_stores_the_answer_under_the_account() -> None:
    db = RecordingDb()
    PlanRepository(db, ()).record_done_op(IVY, "op-a", DoneOp(S1, 4, AT))  # type: ignore[arg-type]
    [(statement, _)] = db.sent
    assert kind(statement) == ("Insert", "plan_done_ops")
    assert values(statement) == {
        "account_id": IVY,
        "op_id": "op-a",
        "session_id": S1,
        "plan_version": 4,
        "created_at": AT,
    }


def test_the_repository_holds_the_library_by_ref() -> None:
    repository = PlanRepository(RecordingDb(), [DRIVES])  # type: ignore[arg-type]
    assert repository.library == {"pb.test.a-wall-drives@1": DRIVES}
