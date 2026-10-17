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

Citation, done and swap columns exist for ST-057 and ST-062, which map them when the aggregate
holds them.
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
class StoredPlan:
    id: uuid.UUID
    owner_id: uuid.UUID
    stale: bool
    plan: TrainingPlan


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
        "excluded_drills": [],
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
                "done_at": None,
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
                    a["position"], drill(a["drill_ref"]), a["minutes"], a["weakness_id"]
                )
                for a in sorted(by_session[s["id"]], key=lambda a: a["position"])
            ),
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
    )


def delete_owned(session: DbSession, owner_id: uuid.UUID) -> int:
    """Every plan row of ``owner_id`` (children cascade from their plan); rows deleted."""
    rows = 0
    for table, column in (
        (plan_done_ops, plan_done_ops.c.account_id),
        (plan_assignments, plan_assignments.c.owner_id),
        (plan_sessions, plan_sessions.c.owner_id),
        (training_plans, training_plans.c.owner_id),
    ):
        result = session.execute(sa.delete(table).where(column == owner_id))
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
        return StoredPlan(root.id, root.owner_id, root.stale, from_rows(rows, self.library))

    def delete_owned(self, owner_id: uuid.UUID) -> int:
        return delete_owned(self.session, owner_id)

    def save(self, owner_id: uuid.UUID, plan: TrainingPlan) -> uuid.UUID:
        """Store ``plan`` as the owner's plan, replacing any earlier one; its new id."""
        delete_owned(self.session, owner_id)
        plan_id = uuid.uuid4()
        rows = to_rows(plan, plan_id=plan_id, owner_id=owner_id)
        at = self.clock()
        self.session.execute(
            sa.insert(training_plans).values(created_at=at, updated_at=at, **rows.plan)
        )
        self.session.execute(sa.insert(plan_sessions), rows.sessions)
        self.session.execute(sa.insert(plan_assignments), rows.assignments)
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
                version=plan.version, content_digest=plan.content_digest(), updated_at=self.clock()
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
            for x in s.assignments:
                changed = self.session.execute(
                    sa.update(plan_assignments)
                    .where(
                        plan_assignments.c.owner_id == owner_id,
                        plan_assignments.c.session_id == slots.get((s.week, s.index)),
                        plan_assignments.c.position == x.position,
                    )
                    .values(drill_ref=x.drill.ref, minutes=x.minutes, weakness_id=x.weakness_id)
                )
                if changed.rowcount != 1:  # type: ignore[attr-defined]
                    raise ValueError(f"plan {plan_id} has no slot {s.week}.{s.index}.{x.position}")
