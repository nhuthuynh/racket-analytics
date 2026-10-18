"""Persistence of the ``TrainingPlan`` aggregate (ST-061a; coaching-plan §1, §5, §9; 0018).

Infrastructure: SQLAlchemy Core tables, the aggregate <-> rows mapping, the owner filter on every
query and the optimistic version check. Only Coaching reads these tables (context-map rule 1).

* ``to_rows`` / ``from_rows`` are pure: rows hold drill refs (``id@version``) and are turned
  back into ``Drill`` values through the pinned library; loading rebuilds the root, so the
  aggregate guards its invariants again and bad rows never become a plan.
* ``PlanRepository.save`` replaces the owner's plan (one per account); ``update`` writes a changed
  plan with ``UPDATE ... WHERE id AND owner_id AND version = :loaded`` (0 rows ->
  ``PlanConflict``) and keeps the session and assignment ids.
* ``delete_owned`` removes every plan row of an account (the purge's ``purge_account``).
* ``save`` also writes the plan's source matches (``plan_source_matches``, coaching-plan §8);
  ``purge_match`` deletes every source-match and citation-rally row naming a purged match and
  marks those plans stale (the purge's ``purge_match``, T4-PL-9 / SEC-S4-TM-03).

Done and swap state (ST-062) is mapped both ways: ``plan_sessions.done_at``,
``plan_assignments.reason_not_for_me`` and ``training_plans.excluded_drills``; ``update`` writes
them. ``record_done_op`` / ``done_op`` keep the idempotent done ops (``plan_done_ops``, unique
``(account_id, op_id)``; api-sprint-04 §3.1); they go with the plan (``delete_owned``).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session as DbSession

from racket.coaching.plan.domain import (
    Drill,
    DrillAssignment,
    PlanWeakness,
    Preferences,
    Session,
    TrainingPlan,
    Unfitted,
)
from racket.platform.db import metadata

Row = dict[str, Any]

training_plans = sa.Table(
    "training_plans",
    metadata,
    sa.Column("id", sa.Uuid(), primary_key=True),
    sa.Column("owner_id", sa.Uuid(), nullable=False, unique=True),
    sa.Column("version", sa.Integer(), nullable=False),
    sa.Column("library_version", sa.String(128), nullable=False),
    sa.Column("preferences", JSONB(), nullable=False),
    sa.Column("weaknesses", JSONB(), nullable=False),
    sa.Column("unfitted", JSONB(), nullable=False),
    sa.Column("excluded_drills", JSONB(), nullable=False),
    sa.Column("limited_data", sa.Boolean(), nullable=False),
    sa.Column("stale", sa.Boolean(), nullable=False),
    sa.Column("content_digest", sa.String(80), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
)
plan_sessions = sa.Table(
    "plan_sessions",
    metadata,
    sa.Column("id", sa.Uuid(), primary_key=True),
    sa.Column("plan_id", sa.Uuid(), sa.ForeignKey("training_plans.id"), nullable=False),
    sa.Column("owner_id", sa.Uuid(), nullable=False),
    sa.Column("week", sa.SmallInteger(), nullable=False),
    sa.Column("session_index", sa.SmallInteger(), nullable=False),
    sa.Column("minutes_budget", sa.SmallInteger(), nullable=False),
    sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
)
plan_assignments = sa.Table(
    "plan_assignments",
    metadata,
    sa.Column("id", sa.Uuid(), primary_key=True),
    sa.Column("session_id", sa.Uuid(), sa.ForeignKey("plan_sessions.id"), nullable=False),
    sa.Column("owner_id", sa.Uuid(), nullable=False),
    sa.Column("position", sa.SmallInteger(), nullable=False),
    sa.Column("drill_ref", sa.String(160), nullable=False),
    sa.Column("minutes", sa.SmallInteger(), nullable=False),
    sa.Column("weakness_id", sa.String(64), nullable=True),
    sa.Column("reason_not_for_me", sa.String(200), nullable=True),
)
plan_citation_rallies = sa.Table(
    "plan_citation_rallies",
    metadata,
    sa.Column("assignment_id", sa.Uuid(), sa.ForeignKey("plan_assignments.id"), primary_key=True),
    sa.Column("match_id", sa.Uuid(), nullable=False),
    sa.Column("rally_id", sa.Uuid(), nullable=False),
    sa.Column("position", sa.SmallInteger(), primary_key=True),
)
plan_source_matches = sa.Table(
    "plan_source_matches",
    metadata,
    sa.Column("plan_id", sa.Uuid(), sa.ForeignKey("training_plans.id"), primary_key=True),
    sa.Column("match_id", sa.Uuid(), primary_key=True),
)
plan_done_ops = sa.Table(
    "plan_done_ops",
    metadata,
    sa.Column("account_id", sa.Uuid(), primary_key=True),
    sa.Column("op_id", sa.String(64), primary_key=True),
    sa.Column("session_id", sa.Uuid(), nullable=False),
    sa.Column("plan_version", sa.Integer(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)


class UnknownDrill(LookupError):
    """A stored drill ref that the pinned library does not hold."""


class PlanConflict(RuntimeError):
    """No plan of this owner with this id at the loaded version (changed or not theirs)."""


@dataclass(frozen=True, slots=True)
class PlanRows:
    plan: Row
    sessions: list[Row]
    assignments: list[Row]


@dataclass(frozen=True, slots=True)
class StoredSession:
    """A saved session's identity and done state, in the plan's (week, index) order; its
    assignment ids in position order (ST-061b: the API names sessions and assignments by id)."""

    id: uuid.UUID
    done_at: datetime | None
    assignment_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True, slots=True)
class DoneOp:
    """A recorded ``POST .../done`` op: its session, the plan version and done time it answered."""

    session_id: uuid.UUID
    plan_version: int
    done_at: datetime


@dataclass(frozen=True, slots=True)
class StoredPlan:
    id: uuid.UUID
    owner_id: uuid.UUID
    stale: bool
    plan: TrainingPlan
    created_at: datetime | None = None
    sessions: tuple[StoredSession, ...] = ()
    source_match_ids: frozenset[uuid.UUID] = frozenset()


def _preferences(p: Preferences) -> Row:
    return {
        "minutes_per_session": p.minutes_per_session,
        "sessions_per_week": p.sessions_per_week,
        "weekly_minutes": p.weekly_minutes,
        "players_available": p.players_available,
        "equipment": sorted(p.equipment),
        "level": p.level,
    }


def to_rows(
    plan: TrainingPlan,
    *,
    plan_id: uuid.UUID,
    owner_id: uuid.UUID,
    new_id: Callable[[], uuid.UUID] = uuid.uuid4,
) -> PlanRows:
    """The rows of migration 0018 for ``plan``; every row names the owner."""
    root = {
        "id": plan_id,
        "owner_id": owner_id,
        "version": plan.version,
        "library_version": plan.library_version,
        "preferences": _preferences(plan.preferences),
        "weaknesses": [{"id": w.id, "target": w.target, "rank": w.rank} for w in plan.weaknesses],
        "unfitted": [{"weakness_id": u.weakness_id, "reason": u.reason} for u in plan.unfitted],
        "excluded_drills": sorted(plan.excluded_drills),
        "limited_data": False,
        "stale": False,
        "content_digest": plan.content_digest(),
    }
    sessions: list[Row] = []
    assignments: list[Row] = []
    for s in plan.sessions:
        session_id = new_id()
        sessions.append(
            {
                "id": session_id,
                "plan_id": plan_id,
                "owner_id": owner_id,
                "week": s.week,
                "session_index": s.index,
                "minutes_budget": s.minutes_budget,
                "done_at": s.done_at,
            }
        )
        assignments += [
            {
                "id": new_id(),
                "session_id": session_id,
                "owner_id": owner_id,
                "position": x.position,
                "drill_ref": x.drill.ref,
                "minutes": x.minutes,
                "weakness_id": x.weakness_id,
                "reason_not_for_me": x.reason_not_for_me,
            }
            for x in s.assignments
        ]
    return PlanRows(root, sessions, assignments)


def from_rows(rows: PlanRows, library: Mapping[str, Drill]) -> TrainingPlan:
    """Rebuild the aggregate; the root checks every invariant (``PlanInvariantBroken``)."""
    plan_id = rows.plan["id"]
    by_session: dict[uuid.UUID, list[Row]] = {s["id"]: [] for s in rows.sessions}
    for s in rows.sessions:
        if s["plan_id"] != plan_id:
            raise ValueError(f"session {s['id']} belongs to another plan")
    for a in rows.assignments:
        if a["session_id"] not in by_session:
            raise ValueError(f"assignment {a['id']} is not in a session of this plan")
        by_session[a["session_id"]].append(a)

    def drill(ref: str) -> Drill:
        if ref not in library:
            raise UnknownDrill(ref)
        return library[ref]

    p = rows.plan["preferences"]
    sessions = [
        Session(
            week=s["week"],
            index=s["session_index"],
            minutes_budget=s["minutes_budget"],
            assignments=tuple(
                DrillAssignment(
                    a["position"],
                    drill(a["drill_ref"]),
                    a["minutes"],
                    a["weakness_id"],
                    a.get("reason_not_for_me"),
                )
                for a in sorted(by_session[s["id"]], key=lambda a: a["position"])
            ),
            done_at=s.get("done_at"),
        )
        for s in sorted(rows.sessions, key=lambda s: (s["week"], s["session_index"]))
    ]
    return TrainingPlan(
        preferences=Preferences(
            minutes_per_session=p["minutes_per_session"],
            sessions_per_week=p["sessions_per_week"],
            players_available=p["players_available"],
            equipment=frozenset(p["equipment"]),
            level=p["level"],
            weekly_minutes=p["weekly_minutes"],
        ),
        weaknesses=tuple(
            PlanWeakness(w["id"], w["target"], w["rank"]) for w in rows.plan["weaknesses"]
        ),
        unfitted=tuple(Unfitted(u["weakness_id"], u["reason"]) for u in rows.plan["unfitted"]),
        sessions=tuple(sessions),
        library_version=rows.plan["library_version"],
        version=rows.plan["version"],
        excluded_drills=frozenset(rows.plan.get("excluded_drills") or ()),
    )


def _identities(rows: PlanRows) -> tuple[StoredSession, ...]:
    by_session: dict[uuid.UUID, list[Row]] = {s["id"]: [] for s in rows.sessions}
    for a in rows.assignments:
        by_session[a["session_id"]].append(a)
    return tuple(
        StoredSession(
            s["id"],
            s["done_at"],
            tuple(a["id"] for a in sorted(by_session[s["id"]], key=lambda a: a["position"])),
        )
        for s in sorted(rows.sessions, key=lambda s: (s["week"], s["session_index"]))
    )


def delete_owned(session: DbSession, owner_id: uuid.UUID) -> int:
    """Every plan row of ``owner_id`` (children cascade from their plan); rows deleted."""
    plans = sa.select(training_plans.c.id).where(training_plans.c.owner_id == owner_id)
    rows = 0
    for table, column in (
        (plan_done_ops, plan_done_ops.c.account_id),
        (plan_source_matches, plan_source_matches.c.plan_id),
        (plan_assignments, plan_assignments.c.owner_id),
        (plan_sessions, plan_sessions.c.owner_id),
        (training_plans, training_plans.c.owner_id),
    ):
        match = column.in_(plans) if table is plan_source_matches else column == owner_id
        result = session.execute(sa.delete(table).where(match))
        rows += int(result.rowcount)  # type: ignore[attr-defined]
    return rows


def purge_match(session: DbSession, match_id: uuid.UUID) -> int:
    """coaching-plan §8, T4-PL-9: every plan citing ``match_id`` becomes stale, and no
    source-match or citation-rally row naming it survives; the number of rows deleted."""
    citing = sa.select(plan_source_matches.c.plan_id).where(
        plan_source_matches.c.match_id == match_id
    )
    session.execute(
        sa.update(training_plans).where(training_plans.c.id.in_(citing)).values(stale=True)
    )
    rows = 0
    for table in (plan_citation_rallies, plan_source_matches):
        result = session.execute(sa.delete(table).where(table.c.match_id == match_id))
        rows += int(result.rowcount)  # type: ignore[attr-defined]
    return rows


def _now() -> datetime:
    return datetime.now(UTC)


class PlanRepository:
    """The owner's plan. Every statement filters by ``owner_id``."""

    def __init__(
        self,
        session: DbSession,
        library: Iterable[Drill],
        *,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self.session = session
        self.library = {d.ref: d for d in library}
        self.clock = clock

    def get(self, owner_id: uuid.UUID) -> StoredPlan | None:
        root = self.session.execute(
            sa.select(training_plans).where(training_plans.c.owner_id == owner_id)
        ).one_or_none()
        if root is None:
            return None
        sessions = self.session.execute(
            sa.select(plan_sessions).where(
                plan_sessions.c.owner_id == owner_id, plan_sessions.c.plan_id == root.id
            )
        ).all()
        assignments = self.session.execute(
            sa.select(plan_assignments).where(
                plan_assignments.c.owner_id == owner_id,
                plan_assignments.c.session_id.in_([s.id for s in sessions]),
            )
        ).all()
        rows = PlanRows(
            dict(root._mapping),
            [dict(s._mapping) for s in sessions],
            [dict(a._mapping) for a in assignments],
        )
        plan = from_rows(rows, self.library)
        sources = self.session.execute(
            sa.select(plan_source_matches.c.match_id).where(
                plan_source_matches.c.plan_id == root.id
            )
        ).scalars()
        return StoredPlan(
            root.id,
            root.owner_id,
            root.stale,
            plan,
            root.created_at,
            _identities(rows),
            frozenset(uuid.UUID(str(m)) for m in sources),
        )

    def delete_owned(self, owner_id: uuid.UUID) -> int:
        return delete_owned(self.session, owner_id)

    def save(
        self,
        owner_id: uuid.UUID,
        plan: TrainingPlan,
        source_match_ids: Iterable[uuid.UUID] = (),
    ) -> uuid.UUID:
        """Store ``plan`` as the owner's plan, replacing any earlier one, with the matches it
        was built from (coaching-plan §8); its new id."""
        delete_owned(self.session, owner_id)
        plan_id = uuid.uuid4()
        rows = to_rows(plan, plan_id=plan_id, owner_id=owner_id)
        at = self.clock()
        self.session.execute(
            sa.insert(training_plans).values(created_at=at, updated_at=at, **rows.plan)
        )
        self.session.execute(sa.insert(plan_sessions), rows.sessions)
        self.session.execute(sa.insert(plan_assignments), rows.assignments)
        sources = [{"plan_id": plan_id, "match_id": m} for m in sorted(set(source_match_ids))]
        if sources:
            self.session.execute(sa.insert(plan_source_matches), sources)
        return plan_id

    def update(
        self, owner_id: uuid.UUID, plan_id: uuid.UUID, plan: TrainingPlan, *, loaded_version: int
    ) -> None:
        """Write a changed plan if the stored one is still ``loaded_version``; ids are kept."""
        result = self.session.execute(
            sa.update(training_plans)
            .where(
                training_plans.c.id == plan_id,
                training_plans.c.owner_id == owner_id,
                training_plans.c.version == loaded_version,
            )
            .values(
                version=plan.version,
                content_digest=plan.content_digest(),
                excluded_drills=sorted(plan.excluded_drills),
                updated_at=self.clock(),
            )
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise PlanConflict(str(plan_id))
        slots = {
            (s.week, s.session_index): s.id
            for s in self.session.execute(
                sa.select(plan_sessions).where(
                    plan_sessions.c.owner_id == owner_id, plan_sessions.c.plan_id == plan_id
                )
            )
        }
        for s in plan.sessions:
            self.session.execute(
                sa.update(plan_sessions)
                .where(
                    plan_sessions.c.owner_id == owner_id,
                    plan_sessions.c.id == slots.get((s.week, s.index)),
                )
                .values(done_at=s.done_at)
            )
            for x in s.assignments:
                changed = self.session.execute(
                    sa.update(plan_assignments)
                    .where(
                        plan_assignments.c.owner_id == owner_id,
                        plan_assignments.c.session_id == slots.get((s.week, s.index)),
                        plan_assignments.c.position == x.position,
                    )
                    .values(
                        drill_ref=x.drill.ref,
                        minutes=x.minutes,
                        weakness_id=x.weakness_id,
                        reason_not_for_me=x.reason_not_for_me,
                    )
                )
                if changed.rowcount != 1:  # type: ignore[attr-defined]
                    raise ValueError(f"plan {plan_id} has no slot {s.week}.{s.index}.{x.position}")

    def done_op(self, owner_id: uuid.UUID, op_id: str) -> DoneOp | None:
        row = self.session.execute(
            sa.select(plan_done_ops).where(
                plan_done_ops.c.account_id == owner_id, plan_done_ops.c.op_id == op_id
            )
        ).one_or_none()
        if row is None:
            return None
        return DoneOp(row.session_id, row.plan_version, row.created_at)

    def record_done_op(self, owner_id: uuid.UUID, op_id: str, result: DoneOp) -> None:
        """Store the op's answer; a concurrent op with the same key raises ``IntegrityError``.
        ``created_at`` holds the answered ``done_at`` (decision row in ST-062.md)."""
        self.session.execute(
            sa.insert(plan_done_ops).values(
                account_id=owner_id,
                op_id=op_id,
                session_id=result.session_id,
                plan_version=result.plan_version,
                created_at=result.done_at,
            )
        )
