"""IT-04-02c (ST-061a; FR-121; NFR-051, NFR-066 b): the plan repository on real Postgres
(migration 0018; coaching-plan §8-§9).

Negative cases first:

* another owner sees nothing: no read, no update and no delete reaches Ivy's plan with Carlos's
  owner id, and the media worker role cannot read any plan table (grants as 0012/0013);
* a save with a version that is no longer the stored one is refused (optimistic concurrency) and
  leaves the stored plan as it was;
* round trip: the plan read back equals the plan saved (preferences, weaknesses, unfitted,
  sessions, drills, minutes, version, content digest), and a second save replaces the owner's
  plan (one plan per account);
* after ``DELETE /me`` and one purge pass, no plan row of the account is left in any plan table
  and no row anywhere holds the account id; another account's plan is untouched.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from racket.coaching.plan.domain import Preferences, TrainingPlan, assemble
from racket.coaching.plan.repository import PlanConflict, PlanRepository
from tests.support import stats as st
from tests.support.api import ApiDriver
from tests.unit.coaching.plan_helpers import TOP_3, reviewed_test_library, solo_wall

pytestmark = pytest.mark.integration

PLAN_TABLES = (
    "training_plans",
    "plan_sessions",
    "plan_assignments",
    "plan_citation_rallies",
    "plan_source_matches",
    "plan_done_ops",
)
WORKER_ROLE = "racket_media_worker"
GROUP = Preferences(
    minutes_per_session=60,
    sessions_per_week=3,
    players_available=4,
    equipment=frozenset({"wall", "half_court", "full_court", "ball_machine", "partner_feeder"}),
    level="intermediate",
    weekly_minutes=150,
)


def _plan(prefs: Preferences) -> TrainingPlan:
    plan = assemble(list(TOP_3), prefs, reviewed_test_library())
    assert isinstance(plan, TrainingPlan), plan
    return plan


def _repo(session: Session) -> PlanRepository:
    return PlanRepository(session, reviewed_test_library())


def _same(read: TrainingPlan, saved: TrainingPlan) -> None:
    assert read.preferences == saved.preferences
    assert read.weaknesses == saved.weaknesses
    assert read.unfitted == saved.unfitted
    assert read.sessions == saved.sessions
    assert (read.library_version, read.version) == (saved.library_version, saved.version)
    assert read.content_digest() == saved.content_digest()


def _new_warm_up_minutes(plan: TrainingPlan, n: int) -> int:
    """Change the warm-up of session ``n`` by one minute (inside 5-10 and the budget)."""
    s = plan.sessions[n]
    minutes = s.assignments[0].minutes
    new = minutes - 1 if minutes > 5 else minutes + 1
    plan.replace_drill(
        week=s.week, index=s.index, position=1, drill=s.assignments[0].drill, minutes=new
    )
    return new


def _plan_rows(engine: Any, owner: uuid.UUID) -> dict[str, int]:
    """Rows of ``owner`` in each plan table (children through their plan or session)."""
    queries = {
        "training_plans": "SELECT count(*) FROM training_plans WHERE owner_id = :o",
        "plan_sessions": "SELECT count(*) FROM plan_sessions WHERE owner_id = :o",
        "plan_assignments": "SELECT count(*) FROM plan_assignments WHERE owner_id = :o",
        "plan_citation_rallies": "SELECT count(*) FROM plan_citation_rallies r "
        "JOIN plan_assignments a ON a.id = r.assignment_id WHERE a.owner_id = :o",
        "plan_source_matches": "SELECT count(*) FROM plan_source_matches m "
        "JOIN training_plans p ON p.id = m.plan_id WHERE p.owner_id = :o",
        "plan_done_ops": "SELECT count(*) FROM plan_done_ops WHERE account_id = :o",
    }
    with engine.connect() as conn:
        counts = {
            t: conn.execute(sa.text(q), {"o": owner}).scalar_one() for t, q in queries.items()
        }
    return {t: int(n) for t, n in counts.items()}


@contextmanager
def _as_worker(engine: Any) -> Iterator[Any]:
    with engine.connect() as conn:
        tx = conn.begin()
        try:
            conn.execute(sa.text(f"SET LOCAL ROLE {WORKER_ROLE}"))
            yield conn
        finally:
            tx.rollback()


# ---------------------------------------------------------------- 1: another owner sees nothing
def test_it_04_02c_another_owner_sees_nothing(db_session: Session) -> None:
    ivy, carlos = uuid.uuid4(), uuid.uuid4()
    plan = _plan(solo_wall())
    plan_id = _repo(db_session).save(ivy, plan)
    db_session.flush()

    assert _repo(db_session).get(carlos) is None
    with pytest.raises(PlanConflict):
        _repo(db_session).update(carlos, plan_id, plan, loaded_version=plan.version)
    assert _repo(db_session).delete_owned(carlos) == 0

    stored = _repo(db_session).get(ivy)
    assert stored is not None
    assert (stored.id, stored.owner_id) == (plan_id, ivy)
    _same(stored.plan, plan)


@pytest.mark.parametrize("table", PLAN_TABLES)
def test_it_04_02c_the_media_worker_cannot_read_plan_tables(db_engine: Any, table: str) -> None:
    with pytest.raises(ProgrammingError, match="permission denied"), _as_worker(db_engine) as conn:
        conn.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1"))


def test_it_04_02c_a_save_on_an_old_version_is_refused(db_session: Session) -> None:
    ivy = uuid.uuid4()
    plan = _plan(solo_wall())
    plan_id = _repo(db_session).save(ivy, plan)
    db_session.flush()
    first = _repo(db_session).get(ivy)
    assert first is not None
    _new_warm_up_minutes(first.plan, 0)
    _repo(db_session).update(ivy, plan_id, first.plan, loaded_version=1)
    db_session.flush()

    stale = _plan(solo_wall())  # still version 1: another request saved in between
    with pytest.raises(PlanConflict):
        _repo(db_session).update(ivy, plan_id, stale, loaded_version=1)
    again = _repo(db_session).get(ivy)
    assert again is not None
    assert again.plan.version == 2
    _same(again.plan, first.plan)


# ---------------------------------------------------------------- 2: round trip
# Fixed ids: str(Preferences) embeds a frozenset whose order follows PYTHONHASHSEED,
# so xdist workers would collect different ids and abort the run.
@pytest.mark.parametrize(
    "prefs",
    [solo_wall(), solo_wall(20, 2), GROUP],
    ids=["solo-wall-30min-3x", "solo-wall-20min-2x", "group-of-4-60min-3x"],
)
def test_it_04_02c_a_saved_plan_reads_back_identical(
    db_session: Session, prefs: Preferences
) -> None:
    ivy = uuid.uuid4()
    plan = _plan(prefs)
    plan_id = _repo(db_session).save(ivy, plan)
    db_session.flush()
    db_session.expire_all()
    stored = _repo(db_session).get(ivy)
    assert stored is not None
    assert (stored.id, stored.owner_id, stored.stale) == (plan_id, ivy, False)
    _same(stored.plan, plan)


def test_it_04_02c_an_update_keeps_the_ids_and_bumps_the_stored_version(
    db_session: Session,
) -> None:
    ivy = uuid.uuid4()
    plan_id = _repo(db_session).save(ivy, _plan(solo_wall()))
    db_session.flush()
    before = (
        db_session.execute(
            sa.text("SELECT id FROM plan_assignments WHERE owner_id = :o ORDER BY id"), {"o": ivy}
        )
        .scalars()
        .all()
    )
    stored = _repo(db_session).get(ivy)
    assert stored is not None
    minutes = _new_warm_up_minutes(stored.plan, 1)
    _repo(db_session).update(ivy, plan_id, stored.plan, loaded_version=1)
    db_session.flush()
    after = (
        db_session.execute(
            sa.text("SELECT id FROM plan_assignments WHERE owner_id = :o ORDER BY id"), {"o": ivy}
        )
        .scalars()
        .all()
    )
    assert after == before
    again = _repo(db_session).get(ivy)
    assert again is not None
    _same(again.plan, stored.plan)
    assert again.plan.sessions[1].assignments[0].minutes == minutes


def test_it_04_02c_a_new_plan_replaces_the_owners_plan(db_session: Session) -> None:
    ivy, carlos = uuid.uuid4(), uuid.uuid4()
    _repo(db_session).save(carlos, _plan(solo_wall()))
    old = _repo(db_session).save(ivy, _plan(solo_wall()))
    new = _repo(db_session).save(ivy, _plan(GROUP))
    db_session.flush()
    assert new != old
    stored = _repo(db_session).get(ivy)
    assert stored is not None
    assert stored.id == new
    assert stored.plan.preferences == GROUP
    count = db_session.execute(
        sa.text("SELECT count(*) FROM training_plans WHERE owner_id = :o"), {"o": ivy}
    ).scalar_one()
    assert count == 1
    other = _repo(db_session).get(carlos)
    assert other is not None
    assert other.plan.preferences == solo_wall()


# ---------------------------------------------------------------- 3: account purge
def test_it_04_02c_the_account_purge_leaves_no_plan_row(api: ApiDriver, committed_db: Any) -> None:
    ivy = uuid.UUID(st.me_id(api, "ivy"))
    carlos = uuid.UUID(st.me_id(api, "carlos"))
    with Session(committed_db) as session:
        _repo(session).save(ivy, _plan(solo_wall()))
        _repo(session).save(carlos, _plan(GROUP))
        session.commit()
    assert all(_plan_rows(committed_db, ivy)[t] > 0 for t in PLAN_TABLES[:3])
    carlos_before = _plan_rows(committed_db, carlos)

    response = st.delete_account(api, "ivy")
    assert response.status_code in st.statscontract.DELETE_OK, response.text
    st.run_purge_once()

    assert _plan_rows(committed_db, ivy) == dict.fromkeys(PLAN_TABLES, 0)
    left = {k: n for k, n in st.rows_holding(committed_db, [str(ivy)]).items() if n}
    assert left == {}, f"rows still hold the account: {left}"
    assert _plan_rows(committed_db, carlos) == carlos_before
    with Session(committed_db) as session:
        kept = _repo(session).get(carlos)
    assert kept is not None
    assert kept.plan.preferences == GROUP
