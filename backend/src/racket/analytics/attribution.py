"""Attribution conservation (ST-045; FR-109; ADR 0003; analytics canvas).

Each rally a side lost is attributed exactly once, per game, split into lost on serve and lost
on receive. Until weakness categories exist (Sprint 4, FR-120), a lost rally's category is the
side's own ending (``unforced_error``, ``forced_error``, ``fault:<kind>`` or
``fault:untagged``); a rally lost to the opponent's winner names no weakness of the side and is
``unattributed``. ``check_conservation`` is the invariant, run on every stats computation; it
raises rather than return a wrong number.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from racket.analytics.sheet import SIDES, CountedRally

UNATTRIBUTED = "unattributed"
PHASES = ("serve", "receive")

# lost[side][game][phase] -> rally numbers; attributed[side][game][phase][category] -> numbers
Lost = dict[str, dict[int, dict[str, list[int]]]]
Attributed = dict[str, dict[int, dict[str, dict[str, list[int]]]]]


class AttributionBroken(AssertionError):
    """FR-109 is violated: a stats computation must not publish its numbers."""


def _phase(rally: CountedRally, side: str) -> str:
    return "serve" if rally.serving_side == side else "receive"


def lost_rallies(counted: Sequence[CountedRally]) -> Lost:
    games = sorted({r.game for r in counted})
    lost: Lost = {s: {g: {p: [] for p in PHASES} for g in games} for s in SIDES}
    for r in counted:
        loser = "B" if r.winning_side == "A" else "A"
        lost[loser][r.game][_phase(r, loser)].append(r.number)
    return lost


def category(rally: CountedRally, side: str) -> str:
    """Why ``side`` lost ``rally``: its own ending, or unattributed (an opponent's winner)."""
    if rally.actor != side:
        return UNATTRIBUTED
    if rally.ending == "fault":
        return f"fault:{rally.fault_kind or 'untagged'}"
    return rally.ending


def attribute_lost_rallies(counted: Sequence[CountedRally]) -> Attributed:
    games = sorted({r.game for r in counted})
    out: Attributed = {s: {g: {p: {} for p in PHASES} for g in games} for s in SIDES}
    for r in counted:
        loser = "B" if r.winning_side == "A" else "A"
        groups = out[loser][r.game][_phase(r, loser)]
        groups.setdefault(category(r, loser), []).append(r.number)
    return out


def check_conservation(
    counted: Sequence[CountedRally],
    attributed: Mapping[str, Mapping[int, Mapping[str, Mapping[str, Sequence[int]]]]],
) -> None:
    """attributed + unattributed = lost, on serve and on receive, for each side and game."""
    lost = lost_rallies(counted)
    problems = []
    for side in SIDES:
        given = attributed.get(side, {})
        for game in sorted(set(lost[side]) | set(given)):
            if game not in given:
                problems.append(f"{side} game {game}: not attributed")
                continue
            if game not in lost[side]:
                problems.append(f"{side} game {game}: attributed but never played")
                continue
            for phase in PHASES:
                got = Counter(n for numbers in given[game].get(phase, {}).values() for n in numbers)
                want = Counter(lost[side][game][phase])
                if got != want:
                    problems.append(
                        f"{side} game {game} {phase}: lost {sorted(want.elements())}, "
                        f"attributed {sorted(got.elements())}"
                    )
    if problems:
        raise AttributionBroken("; ".join(problems))
