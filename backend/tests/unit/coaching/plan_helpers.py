"""Test drills, weaknesses and an independent plan checker for ST-056 (FR-121; QD-PL-01..03).

``plan_problems`` re-states the plan rules from coaching-plan §5 and the COACH-4 warm-up rule
without using the aggregate's own check, so a property test over ``assemble`` is not circular.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from racket.coaching.plan.domain import (
    Drill,
    Infeasible,
    PlanWeakness,
    Preferences,
    TrainingPlan,
)

LEVEL_ORDER = ("beginner", "intermediate", "advanced")


def drill_doc(
    drill_id: str,
    *,
    targets: Sequence[str] = ("AN-04",),
    skills: Sequence[str] = (),
    players: int = 1,
    needs: Sequence[str] = (),
    minutes: tuple[int, int] = (8, 15),
    levels: tuple[str, str] = ("beginner", "advanced"),
    status: str = "coach-reviewed",
    version: int = 1,
    deprecated_by: str | None = None,
) -> dict[str, Any]:
    """A drill document in the shape of ``content/drills/<id>/v<n>.json`` (drill schema v1)."""
    doc: dict[str, Any] = {
        "id": drill_id,
        "version": version,
        "name": drill_id,
        "summary": "Test drill for ST-056, not coaching content.",
        "skills": list(skills),
        "target_metrics": list(targets),
        "level_min": levels[0],
        "level_max": levels[1],
        "duration_min": minutes[0],
        "duration_max": minutes[1],
        "players": players,
        "needs": list(needs),
        "equipment": ["balls", "paddle"],
        "setup": ["Test setup"],
        "success_criterion": "8 of 10",
        "progressions": [],
        "regressions": [],
        "safety_notes": "",
        "coach_rationale": "Test drill (judgment)",
        "review_status": status,
    }
    if deprecated_by is not None:
        doc["deprecated_by"] = deprecated_by
    return doc


def drill(drill_id: str, **kw: Any) -> Drill:
    return Drill.from_document(drill_doc(drill_id, **kw))


def warm_up(drill_id: str, **kw: Any) -> Drill:
    kw.setdefault("minutes", (5, 10))
    kw.setdefault("skills", ("warm-up",))
    return drill(drill_id, **kw)


def reviewed_test_library() -> list[Drill]:
    """Warm-ups for 1 and 2 players; AN-04 drills for a wall, a ball machine and 4 players; a
    draft and a deprecated AN-04 drill; an AN-05 serve drill; AN-07 forced-error drills that need
    a partner feeder (2 players) or a ball machine."""
    return [
        warm_up("pb.test.shadow-warm-up"),
        warm_up("pb.test.wall-warm-up", needs=("wall",), minutes=(5, 8)),
        warm_up("pb.test.partner-warm-up", players=2, needs=("half_court",)),
        drill("pb.test.wall-dinks", needs=("wall",), minutes=(8, 15)),
        drill("pb.test.machine-drops", needs=("ball_machine",), minutes=(10, 15)),
        drill("pb.test.four-player-drops", players=4, needs=("full_court",), minutes=(10, 20)),
        drill("pb.test.draft-drops", needs=("wall",), status="draft"),
        drill("pb.test.old-drops", deprecated_by="pb.test.wall-dinks@1"),
        drill("pb.test.serve-target", targets=("AN-05", "AN-01"), minutes=(5, 10)),
        drill(
            "pb.test.pressure-volleys",
            targets=("AN-07",),
            skills=("share:forced-error",),
            players=2,
            needs=("partner_feeder",),
            minutes=(8, 15),
        ),
        drill(
            "pb.test.machine-pressure",
            targets=("AN-07",),
            skills=("share:forced-error",),
            needs=("ball_machine",),
            minutes=(8, 12),
        ),
    ]


TOP_3 = (
    PlanWeakness("unforced_errors", "AN-04", 1),
    PlanWeakness("serve_faults", "AN-05", 2),
    PlanWeakness("errors_under_pressure", "AN-07:forced-error", 3),
)


def solo_wall(minutes: int = 30, sessions: int = 3) -> Preferences:
    return Preferences(
        minutes_per_session=minutes,
        sessions_per_week=sessions,
        players_available=1,
        equipment=frozenset({"wall"}),
        level="intermediate",
    )


def plan_targets(d: Drill) -> set[str]:
    out: set[str] = set()
    for metric in d.target_metrics:
        if metric != "AN-07":
            out.add(metric)
            continue
        out |= {f"AN-07:{s[6:]}" for s in d.skills if s in ("share:fault", "share:forced-error")}
    return out


def _fits_setup(d: Drill, prefs: Preferences) -> bool:
    level = LEVEL_ORDER.index(prefs.level)
    return (
        d.players <= prefs.players_available
        and d.needs <= prefs.equipment
        and LEVEL_ORDER.index(d.level_min) <= level <= LEVEL_ORDER.index(d.level_max)
        and d.review_status in ("coach-reviewed", "verified")
        and not d.deprecated
    )


def plan_problems(
    plan: TrainingPlan | Infeasible,
    prefs: Preferences,
    weaknesses: Iterable[PlanWeakness],
    library: Iterable[Drill],
) -> list[str]:
    """Every broken plan rule, as text; [] for a plan that keeps them all. An ``Infeasible`` is
    a problem only when the library holds a fitting warm-up and a fitting drill for a weakness
    (the assembly then had a plan to give)."""
    weaknesses = sorted(weaknesses, key=lambda w: (w.rank, w.id))
    library = list(library)
    weekly = prefs.weekly_minutes or prefs.minutes_per_session * prefs.sessions_per_week
    budget = min(prefs.minutes_per_session, weekly // prefs.sessions_per_week)
    cap = budget * 2 // 5
    if isinstance(plan, Infeasible):
        return _infeasible_problems(prefs, weaknesses, library, cap)
    found: list[str] = []
    refs = {d.ref for d in library}
    by_weakness = {w.id: w for w in weaknesses}
    unfitted = {u.weakness_id for u in plan.unfitted}
    keys = [(s.week, s.index) for s in plan.sessions]
    expected = [(w, i) for w in (1, 2) for i in range(1, prefs.sessions_per_week + 1)]
    if keys != expected:
        found.append(f"sessions {keys} != {expected}")
    for week in (1, 2):
        total = sum(s.total_minutes for s in plan.sessions if s.week == week)
        if total > weekly:
            found.append(f"week {week}: {total} > {weekly} minutes")
    for s in plan.sessions:
        where = f"week {s.week} session {s.index}"
        if s.total_minutes > budget:
            found.append(f"{where}: {s.total_minutes} > {budget} minutes")
        if not s.assignments or "warm-up" not in s.assignments[0].drill.skills:
            found.append(f"{where}: does not start with a warm-up")
        elif not 5 <= s.assignments[0].minutes <= 10:
            found.append(f"{where}: warm-up of {s.assignments[0].minutes} minutes")
        if len({a.drill.ref for a in s.assignments}) != len(s.assignments):
            found.append(f"{where}: a drill appears twice")
        for pos, a in enumerate(s.assignments, start=1):
            at = f"{where} drill {pos} {a.drill.ref}"
            d = a.drill
            if a.position != pos:
                found.append(f"{at}: position {a.position}")
            if d.ref not in refs:
                found.append(f"{at}: not in the library")
            if not _fits_setup(d, prefs):
                found.append(f"{at}: does not fit the setup or is not reviewed")
            if a.minutes > cap:
                found.append(f"{at}: {a.minutes} > 40% cap {cap}")
            if not d.duration_min <= a.minutes <= d.duration_max:
                found.append(f"{at}: {a.minutes} outside {d.duration_min}..{d.duration_max}")
            if pos > 1:
                w = by_weakness.get(a.weakness_id or "")
                if "warm-up" in d.skills:
                    found.append(f"{at}: a second warm-up")
                if w is None or w.id in unfitted or w.target not in plan_targets(d):
                    found.append(f"{at}: does not train weakness {a.weakness_id}")
            elif a.weakness_id is not None:
                found.append(f"{at}: the warm-up is assigned a weakness")
    for w in weaknesses[:3]:
        fits = any(_weakness_drill(d, w, prefs, cap) for d in library)
        if fits == (w.id in unfitted):
            found.append(f"weakness {w.id}: unfitted={w.id in unfitted} but a drill fits={fits}")
    return found


def _weakness_drill(d: Drill, w: PlanWeakness, prefs: Preferences, cap: int) -> bool:
    return (
        _fits_setup(d, prefs)
        and "warm-up" not in d.skills
        and w.target in plan_targets(d)
        and d.duration_min <= cap
    )


def _infeasible_problems(
    prefs: Preferences, weaknesses: list[PlanWeakness], library: list[Drill], cap: int
) -> list[str]:
    warm = any(
        _fits_setup(d, prefs)
        and "warm-up" in d.skills
        and max(5, d.duration_min) <= min(10, d.duration_max, cap)
        for d in library
    )
    work = any(_weakness_drill(d, w, prefs, cap) for d in library for w in weaknesses[:3])
    return ["infeasible although a warm-up and a weakness drill fit"] if warm and work else []
