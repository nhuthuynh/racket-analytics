"""The ``TrainingPlan`` aggregate and its value objects (ST-056; FR-121; QD-PL-01..03).

Pure domain (coaching-plan §5): standard library only, no clock, no randomness, no ids. The root
checks every invariant on creation and after every change; a violation raises
``PlanInvariantBroken`` and leaves the plan as it was.

Follow-through commands (ST-062; FR-124; coaching-plan §5, §7): ``mark_done`` and ``undo_done``.
Sessions are named by ``(week, index)`` (the service maps the API's ids). Each accepted change
returns its event and adds 1 to ``version``; a no-op returns None; a refusal (``KeyError``)
changes nothing.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

LEVELS = ("beginner", "intermediate", "advanced")
NEEDS = frozenset({"wall", "half_court", "full_court", "ball_machine", "partner_feeder"})
REVIEWED = frozenset({"coach-reviewed", "verified"})
WARM_UP = "warm-up"
WARM_UP_MINUTES = (5, 10)  # COACH-4 drill-review-checklist §2
DRILL_SHARE = (2, 5)  # no drill over 40% of its session (QD-PL-03)
MAX_WEAKNESSES = 3  # FR-121: the top 3
WEEKS = 2  # FR-121: a 2-week plan
MIN_SESSION = 15  # api-sprint-04 §2.1
NO_DRILL_FITS = "no drill fits your setup"
_SHARES = {"share:fault": "AN-07:fault", "share:forced-error": "AN-07:forced-error"}


class InvalidPreferences(ValueError):
    """Preferences outside the ranges of api-sprint-04 §2.1."""


class PlanInvariantBroken(ValueError):
    """A plan would break QD-PL-01..03 or the plan shape; ``violations`` names each rule."""

    def __init__(self, violations: Sequence[str]) -> None:
        super().__init__("; ".join(violations))
        self.violations = list(violations)


@dataclass(frozen=True, slots=True)
class Drill:
    """A library drill version, as the plan sees it (drill schema v1 fields)."""

    id: str
    version: int
    skills: frozenset[str]
    target_metrics: tuple[str, ...]
    level_min: str
    level_max: str
    duration_min: int
    duration_max: int
    players: int
    needs: frozenset[str]
    review_status: str
    deprecated: bool = False

    @classmethod
    def from_document(cls, doc: Mapping[str, Any]) -> Drill:
        """Translate a parsed ``content/drills/<id>/v<n>.json`` (already lint-checked)."""
        return cls(
            id=doc["id"],
            version=doc["version"],
            skills=frozenset(doc["skills"]),
            target_metrics=tuple(doc["target_metrics"]),
            level_min=doc["level_min"],
            level_max=doc["level_max"],
            duration_min=doc["duration_min"],
            duration_max=doc["duration_max"],
            players=doc["players"],
            needs=frozenset(doc["needs"]),
            review_status=doc["review_status"],
            deprecated="deprecated_by" in doc,
        )

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.version}"

    @property
    def is_warm_up(self) -> bool:
        return WARM_UP in self.skills

    @property
    def is_reviewed(self) -> bool:
        return self.review_status in REVIEWED

    @property
    def plan_targets(self) -> frozenset[str]:
        """weakness-catalogue §5: the metric ids, with AN-07 split by its share skills."""
        found = {m for m in self.target_metrics if m != "AN-07"}
        if "AN-07" in self.target_metrics:
            found |= {target for skill, target in _SHARES.items() if skill in self.skills}
        return frozenset(found)

    def fits(self, prefs: Preferences) -> bool:
        """QD-PL-02: players, needs, level, reviewed and not deprecated."""
        level = LEVELS.index(prefs.level)
        return (
            self.players <= prefs.players_available
            and self.needs <= prefs.equipment
            and LEVELS.index(self.level_min) <= level <= LEVELS.index(self.level_max)
            and self.is_reviewed
            and not self.deprecated
        )


@dataclass(frozen=True, slots=True)
class Preferences:
    minutes_per_session: int
    sessions_per_week: int
    players_available: int
    equipment: frozenset[str]
    level: str
    weekly_minutes: int | None = None

    def __post_init__(self) -> None:
        problems = []
        if not MIN_SESSION <= self.minutes_per_session <= 180:
            problems.append("minutes_per_session")
        if not 1 <= self.sessions_per_week <= 7:
            problems.append("sessions_per_week")
        elif self.weekly_minutes is not None and (
            self.weekly_minutes < self.sessions_per_week * MIN_SESSION
        ):
            problems.append("weekly_minutes")
        if not 1 <= self.players_available <= 4:
            problems.append("players_available")
        if not self.equipment <= NEEDS:
            problems.append("equipment")
        if self.level not in LEVELS:
            problems.append("level")
        if problems:
            raise InvalidPreferences(", ".join(problems))

    @property
    def weekly_total(self) -> int:
        if self.weekly_minutes is None:
            return self.minutes_per_session * self.sessions_per_week
        return self.weekly_minutes

    @property
    def minutes_budget(self) -> int:
        """QD-PL-01: min(minutes per session, floor(weekly minutes / sessions per week))."""
        return min(self.minutes_per_session, self.weekly_total // self.sessions_per_week)

    @property
    def drill_cap(self) -> int:
        """QD-PL-03: floor(40% of the session budget)."""
        return self.minutes_budget * DRILL_SHARE[0] // DRILL_SHARE[1]


@dataclass(frozen=True, slots=True)
class PlanWeakness:
    """A ranked weakness the plan trains: its catalogue id, plan target (weakness-catalogue §5:
    a metric id, or ``AN-07:fault`` / ``AN-07:forced-error``) and rank (1 = most rallies lost)."""

    id: str
    target: str
    rank: int


@dataclass(frozen=True, slots=True)
class Unfitted:
    """A top-3 weakness for which no drill fits the player's setup."""

    weakness_id: str
    reason: str = "no_drill_fits"

    @property
    def text(self) -> str:
        return NO_DRILL_FITS


@dataclass(frozen=True, slots=True)
class DrillAssignment:
    position: int
    drill: Drill
    minutes: int
    weakness_id: str | None  # None for the warm-up


@dataclass(frozen=True, slots=True)
class Session:
    week: int
    index: int
    minutes_budget: int
    assignments: tuple[DrillAssignment, ...]
    done_at: datetime | None = None

    @property
    def total_minutes(self) -> int:
        return sum(x.minutes for x in self.assignments)


@dataclass(frozen=True, slots=True)
class SessionMarkedDone:
    week: int
    index: int
    version: int


@dataclass(frozen=True, slots=True)
class SessionDoneUndone:
    week: int
    index: int
    version: int


def violations(
    prefs: Preferences,
    weaknesses: Sequence[PlanWeakness],
    unfitted: Sequence[Unfitted],
    sessions: Sequence[Session],
) -> list[str]:
    """Every broken plan rule (coaching-plan §5), prefixed by its id; [] when all hold."""
    found = _shape(prefs, weaknesses, unfitted, sessions)
    for week in range(1, WEEKS + 1):
        total = sum(s.total_minutes for s in sessions if s.week == week)
        if total > prefs.weekly_total:
            found.append(f"QD-PL-01: week {week} totals {total} > {prefs.weekly_total} minutes")
    targets = {w.id: w.target for w in weaknesses}
    fitted = set(targets) - {u.weakness_id for u in unfitted}
    for s in sessions:
        found += _session(s, prefs, targets, fitted)
    return found


def _shape(
    prefs: Preferences,
    weaknesses: Sequence[PlanWeakness],
    unfitted: Sequence[Unfitted],
    sessions: Sequence[Session],
) -> list[str]:
    found = []
    keys = [(s.week, s.index) for s in sessions]
    per_week = range(1, prefs.sessions_per_week + 1)
    if keys != [(w, i) for w in range(1, WEEKS + 1) for i in per_week]:
        found.append(f"plan: sessions {keys} are not {WEEKS} weeks x {prefs.sessions_per_week}")
    ids = [w.id for w in weaknesses]
    ranks = sorted(w.rank for w in weaknesses)
    if len(ids) > MAX_WEAKNESSES or len(set(ids)) != len(ids):
        found.append(f"plan: weaknesses {ids} are not up to {MAX_WEAKNESSES} distinct ones")
    if ranks != list(range(1, len(ranks) + 1)):
        found.append(f"plan: weakness ranks {ranks} are not 1..{len(ranks)}")
    if stray := sorted({u.weakness_id for u in unfitted} - set(ids)):
        found.append(f"plan: unfitted {stray} are not plan weaknesses")
    return found


def _session(
    s: Session, prefs: Preferences, targets: Mapping[str, str], fitted: set[str]
) -> list[str]:
    where = f"week {s.week} session {s.index}"
    found = []
    if s.minutes_budget != prefs.minutes_budget:
        found.append(f"plan: {where} budget {s.minutes_budget} != {prefs.minutes_budget}")
    if s.total_minutes > prefs.minutes_budget:
        found.append(f"QD-PL-01: {where} totals {s.total_minutes} > {prefs.minutes_budget}")
    if [x.position for x in s.assignments] != list(range(1, len(s.assignments) + 1)):
        found.append(f"plan: {where} positions are not 1..{len(s.assignments)}")
    if len({x.drill.ref for x in s.assignments}) != len(s.assignments):
        found.append(f"plan: {where} has a drill twice")
    if not s.assignments or not s.assignments[0].drill.is_warm_up:
        found.append(f"QD-PL-03: {where} does not start with a warm-up")
    for x in s.assignments:
        found += _assignment(x, f"{where} drill {x.position} {x.drill.ref}", prefs, targets, fitted)
    return found


def _assignment(
    x: DrillAssignment, at: str, prefs: Preferences, targets: Mapping[str, str], fitted: set[str]
) -> list[str]:
    found = []
    d = x.drill
    if not d.duration_min <= x.minutes <= d.duration_max:
        found.append(f"QD-PL-01: {at} {x.minutes} min outside {d.duration_min}..{d.duration_max}")
    if not d.fits(prefs):
        found.append(f"QD-PL-02: {at} does not fit the setup or is not a reviewed drill")
    if x.minutes > prefs.drill_cap:
        found.append(f"QD-PL-03: {at} {x.minutes} min > 40% cap {prefs.drill_cap}")
    if x.position == 1:
        lo, hi = WARM_UP_MINUTES
        if d.is_warm_up and not lo <= x.minutes <= hi:
            found.append(f"QD-PL-03: {at} warm-up of {x.minutes} min is not {lo}-{hi}")
        if x.weakness_id is not None:
            found.append(f"plan: {at} the warm-up is given weakness {x.weakness_id}")
        return found
    if d.is_warm_up:
        found.append(f"QD-PL-03: {at} is a second warm-up")
    w = x.weakness_id
    if w is None or w not in fitted or targets[w] not in d.plan_targets:
        found.append(f"plan: {at} does not train a fitted weakness ({w})")
    return found


@dataclass(eq=False, slots=True)
class TrainingPlan:
    """The aggregate root: a 2-week plan of sessions of drill assignments."""

    preferences: Preferences
    weaknesses: tuple[PlanWeakness, ...]
    unfitted: tuple[Unfitted, ...]
    sessions: tuple[Session, ...]
    library_version: str = ""
    version: int = field(default=1)

    def __post_init__(self) -> None:
        self.weaknesses = tuple(self.weaknesses)
        self.unfitted = tuple(self.unfitted)
        self.sessions = tuple(self.sessions)
        self._guard(self.sessions)

    def _guard(self, sessions: Sequence[Session]) -> None:
        if found := violations(self.preferences, self.weaknesses, self.unfitted, sessions):
            raise PlanInvariantBroken(found)

    def _change(self, sessions: tuple[Session, ...]) -> None:
        """The one path every command takes: check, then apply and bump the version."""
        self._guard(sessions)
        self.sessions = sessions
        self.version += 1

    def replace_drill(
        self, *, week: int, index: int, position: int, drill: Drill, minutes: int
    ) -> None:
        """Put ``drill`` for ``minutes`` at one assignment, keeping its weakness (the building
        block of ST-062's swap). KeyError when there is no such assignment."""
        for n, s in enumerate(self.sessions):
            if (s.week, s.index) == (week, index) and 1 <= position <= len(s.assignments):
                old = s.assignments[position - 1]
                new = replace(old, drill=drill, minutes=minutes)
                assignments = (*s.assignments[: position - 1], new, *s.assignments[position:])
                changed = replace(s, assignments=assignments)
                self._change((*self.sessions[:n], changed, *self.sessions[n + 1 :]))
                return
        raise KeyError(f"no assignment at week {week} session {index} position {position}")

    def _session_at(self, week: int, index: int) -> int:
        for n, s in enumerate(self.sessions):
            if (s.week, s.index) == (week, index):
                return n
        raise KeyError(f"no session at week {week} session {index}")

    def _with_session(self, n: int, s: Session) -> tuple[Session, ...]:
        return (*self.sessions[:n], s, *self.sessions[n + 1 :])

    def mark_done(self, *, week: int, index: int, at: datetime) -> SessionMarkedDone | None:
        """Mark one session done at ``at``; None (no change) when it is done already."""
        n = self._session_at(week, index)
        s = self.sessions[n]
        if s.done_at is not None:
            return None
        self._change(self._with_session(n, replace(s, done_at=at)))
        return SessionMarkedDone(week, index, self.version)

    def undo_done(self, *, week: int, index: int) -> SessionDoneUndone | None:
        """Clear one session's done mark; None (no change) when it is not done."""
        n = self._session_at(week, index)
        s = self.sessions[n]
        if s.done_at is None:
            return None
        self._change(self._with_session(n, replace(s, done_at=None)))
        return SessionDoneUndone(week, index, self.version)

    def content(self) -> dict[str, Any]:
        """The plan's content (coaching-plan §6 step 5): no ids, version, clock or done state."""
        p = self.preferences
        return {
            "library_version": self.library_version,
            "preferences": {
                "minutes_per_session": p.minutes_per_session,
                "sessions_per_week": p.sessions_per_week,
                "weekly_minutes": p.weekly_total,
                "players_available": p.players_available,
                "equipment": sorted(p.equipment),
                "level": p.level,
            },
            "weaknesses": [
                {"id": w.id, "target": w.target, "rank": w.rank} for w in self.weaknesses
            ],
            "unfitted": [{"weakness_id": u.weakness_id, "reason": u.reason} for u in self.unfitted],
            "sessions": [
                {
                    "week": s.week,
                    "index": s.index,
                    "minutes_budget": s.minutes_budget,
                    "assignments": [
                        {
                            "position": x.position,
                            "drill": x.drill.ref,
                            "minutes": x.minutes,
                            "weakness_id": x.weakness_id,
                        }
                        for x in s.assignments
                    ],
                }
                for s in self.sessions
            ],
        }

    def content_digest(self) -> str:
        blob = json.dumps(self.content(), sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()
