"""Rules-only plan assembly (ST-056; FR-121; coaching-plan §6). A pure, deterministic function.

1. Eligible drills (QD-PL-02) sorted by ``(id, version)``; warm-ups are those that can be given
   5-10 minutes under the 40% cap; each top-3 weakness gets the non-warm-up drills that hit its
   plan target and whose ``duration_min`` fits under the cap.
2. A weakness with no such drill is ``Unfitted`` ("no drill fits your setup"); the weights 3:2:1
   go to the fitted weaknesses in rank order, so an unfitted one's share passes down.
3. Session s (0..2n-1) starts with warm-up ``s mod W`` at min(duration_max, 10, cap) minutes; the
   rest of the budget is filled by a smooth weighted round-robin over the fitted weaknesses (one
   state for the whole plan), each weakness rotating through its drills, at min(duration_max, cap,
   remaining) minutes, skipping a drill already in the session or whose minimum does not fit.
4. No eligible warm-up, or no fitted weakness: ``Infeasible("no_plan_fits")``.

Every order is a total key; no clock, no randomness; the result is a checked ``TrainingPlan``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from racket.coaching.plan.domain.model import (
    MAX_WEAKNESSES,
    WEEKS,
    Drill,
    DrillAssignment,
    PlanWeakness,
    Preferences,
    Session,
    TrainingPlan,
    Unfitted,
    warm_up_minutes,
)

RANK_WEIGHTS = (3, 2, 1)  # judgment, pinned in docs/sprints/04/decisions/ST-056.md


@dataclass(frozen=True, slots=True)
class Infeasible:
    """No plan: ``no_weakness`` (empty ranking) or ``no_plan_fits`` (api-sprint-04 §2.1)."""

    reason: str


class _RoundRobin:
    """Smooth weighted round-robin over the weaknesses still open in a session. Only a placed
    drill moves the state, so the placements follow the 3:2:1 sequence (A B A C B A ...)."""

    def __init__(self, ids: Sequence[str]) -> None:
        self._order = list(ids)
        self._weight = dict(zip(ids, RANK_WEIGHTS, strict=False))
        self._current = dict.fromkeys(ids, 0)

    def _open(self, open_ids: set[str]) -> list[str]:
        return [w for w in self._order if w in open_ids]

    def pick(self, open_ids: set[str]) -> str:
        return max(
            self._open(open_ids),
            key=lambda w: (self._current[w] + self._weight[w], -self._order.index(w)),
        )

    def placed(self, pick: str, open_ids: set[str]) -> None:
        candidates = self._open(open_ids)
        for w in candidates:
            self._current[w] += self._weight[w]
        self._current[pick] -= sum(self._weight[w] for w in candidates)


def assemble(
    weaknesses: Iterable[PlanWeakness],
    prefs: Preferences,
    library: Iterable[Drill],
    library_version: str = "",
) -> TrainingPlan | Infeasible:
    top = sorted(weaknesses, key=lambda w: (w.rank, w.id))[:MAX_WEAKNESSES]
    if not top:
        return Infeasible("no_weakness")
    cap = prefs.drill_cap
    eligible = sorted((d for d in library if d.fits(prefs)), key=lambda d: (d.id, d.version))
    warm_ups = [d for d in eligible if d.is_warm_up and warm_up_minutes(d, cap) is not None]
    pools = {w.id: _pool(w, eligible, cap) for w in top}
    fitted = {w: pool for w, pool in pools.items() if pool}
    if not warm_ups or not fitted:
        return Infeasible("no_plan_fits")
    picker = _RoundRobin(list(fitted))
    uses = dict.fromkeys(fitted, 0)
    sessions = []
    for s in range(WEEKS * prefs.sessions_per_week):
        week, index = divmod(s, prefs.sessions_per_week)
        assignments = _fill(warm_ups[s % len(warm_ups)], prefs, picker, fitted, uses)
        sessions.append(Session(week + 1, index + 1, prefs.minutes_budget, assignments))
    return TrainingPlan(
        preferences=prefs,
        weaknesses=tuple(top),
        unfitted=tuple(Unfitted(w) for w, pool in pools.items() if not pool),
        sessions=tuple(sessions),
        library_version=library_version,
    )


def _pool(w: PlanWeakness, eligible: Sequence[Drill], cap: int) -> list[Drill]:
    """The drills that can fill a slot of ``w``: not a warm-up, hit its plan target, and their
    minimum fits under the 40% cap (so they fit after any warm-up: budget - cap >= cap)."""
    return [
        d
        for d in eligible
        if not d.is_warm_up and w.target in d.plan_targets and d.duration_min <= cap
    ]


def _fill(
    warm: Drill,
    prefs: Preferences,
    picker: _RoundRobin,
    pools: Mapping[str, Sequence[Drill]],
    uses: dict[str, int],
) -> tuple[DrillAssignment, ...]:
    cap = prefs.drill_cap
    minutes = warm_up_minutes(warm, cap) or 0
    out = [DrillAssignment(1, warm, minutes, None)]
    used = {warm.ref}
    remaining = prefs.minutes_budget - minutes
    open_ids = set(pools)
    while open_ids:
        w = picker.pick(open_ids)
        pool = pools[w]
        room = min(cap, remaining)
        rotated = (pool[(uses[w] + k) % len(pool)] for k in range(len(pool)))
        d = next((d for d in rotated if d.ref not in used and d.duration_min <= room), None)
        if d is None:
            open_ids.discard(w)
            continue
        given = min(d.duration_max, room)
        out.append(DrillAssignment(len(out) + 1, d, given, w))
        picker.placed(w, open_ids)
        used.add(d.ref)
        remaining -= given
        uses[w] += 1
    return tuple(out)
