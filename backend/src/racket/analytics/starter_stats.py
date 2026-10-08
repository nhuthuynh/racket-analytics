"""Starter stats AN-01..AN-07 over the projected score sheet (ST-044; FR-100, FR-101; NFR-004).

Pure functions, no I/O (sprint-03 §3.4). The input is the sheet Match & Scoring projects
(``matches.scorebook.domain.projection.project``, ST-026), read as plain JSON, so this module
imports nothing of that context. Formulas follow ``docs/domain/metric-dictionary.md`` v0.1
(coach judgment, every entry ``draft`` until COACH-1):

* rule 0.1: ``replay`` rows and rows the sheet could not score (``needs_decision``) are in no
  numerator or denominator;
* rule 0.2: a ``winner`` is the winning side's; an error or fault is the losing side's; the
  player is known only when ``responsible_player`` is tagged, never spread;
* rule 0.3: every metric carries n; proportions a 95% Wilson interval; flags from
  ``LowSamplePolicy`` (config);
* a point is scored by the rally winner when the sheet's score total goes up by one: true under
  side-out and rally scoring alike, so no scoring rule is re-implemented here (rule 0.5).

Rally references (``rallies``) are the sheet's match-wide 1-based ``number`` values, the ids the
evidence lists use (FR-103). Every metric that reads the score sequence inherits the preset's
PROVISIONAL-UNVERIFIED status (ADR 0009, ADR 0023).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from racket.analytics.attribution import attribute_lost_rallies, check_conservation
from racket.analytics.sheet import (
    SIDES,
    CountedRally,
    counted_rallies,
    game_numbers_in_scope,
)
from racket.analytics.uncertainty import LowSamplePolicy, wilson

METRICS = ("AN-01", "AN-02", "AN-03", "AN-04", "AN-05", "AN-06", "AN-07")
CATEGORIES = ("winner", "unforced_error", "forced_error", "fault")
RUN_BUCKETS = ("1", "2", "3", "4", "5+")
Stats = dict[str, dict[str, dict[str, Any]]]
__all__ = ["METRICS", "CountedRally", "Stats", "counted_rallies", "starter_stats"]


def _round(value: float | None, places: int) -> float | None:
    return None if value is None else round(value, places)


def proportion(k: int, rallies: Sequence[int], policy: LowSamplePolicy) -> dict[str, Any]:
    n = len(rallies)
    ci = wilson(k, n)
    return {
        "k": k,
        "n": n,
        "value": _round(k / n if n else None, 4),
        "ci_low": _round(ci.low if ci else None, 4),
        "ci_high": _round(ci.high if ci else None, 4),
        "low_sample": policy.proportion_flagged(k, n),
        "rallies": list(rallies),
    }


def _turns(counted: Sequence[CountedRally], side: str) -> int:
    """Service turns of ``side``: a turn starts when it gains the serve or a game starts."""
    turns, prev = 0, None
    for r in counted:
        if prev is None or r.game != prev.game or r.serving_side != prev.serving_side:
            turns += r.serving_side == side
        prev = r
    return turns


def _runs(counted: Sequence[CountedRally], side: str) -> list[tuple[int, int]]:
    """``(game, length)`` of each maximal point run of ``side``; serve-only rallies do not break
    a run, a game end does (AN-06)."""
    runs: list[tuple[int, int]] = []
    holder, length, game = None, 0, None
    for r in counted:
        if r.game != game:
            if holder == side and game is not None:
                runs.append((game, length))
            holder, length, game = None, 0, r.game
        if r.point_to is None:
            continue
        if r.point_to == holder:
            length += 1
            continue
        if holder == side:
            runs.append((game, length))
        holder, length = r.point_to, 1
    if holder == side and game is not None:
        runs.append((game, length))
    return runs


def _side_stats(
    counted: Sequence[CountedRally], side: str, game_numbers: Sequence[int], policy: LowSamplePolicy
) -> dict[str, dict[str, Any]]:
    games = len(game_numbers)
    served = [r for r in counted if r.serving_side == side]
    received = [r for r in counted if r.serving_side != side]
    out: dict[str, dict[str, Any]] = {}
    out["AN-01"] = proportion(
        sum(r.winning_side == side for r in served), [r.number for r in served], policy
    )
    out["AN-02"] = proportion(
        sum(r.winning_side == side for r in received), [r.number for r in received], policy
    )

    scoring = [r for r in served if r.point_to == side]
    turns = _turns(counted, side)
    out["AN-03"] = {
        "points": len(scoring),
        "turns": turns,
        "value": _round(len(scoring) / turns if turns else None, 1),
        "low_sample": policy.turns_flagged(turns),
        "rallies": [r.number for r in scoring],
    }

    ue = [r for r in counted if r.ending == "unforced_error" and r.actor == side]
    by_player = Counter(r.responsible_player for r in ue if r.responsible_player)
    out["AN-04"] = {
        "count": len(ue),
        "games": games,
        "value": _round(len(ue) / games if games else None, 1),
        "by_player": dict(sorted(by_player.items())),
        "player_not_tagged": sum(r.responsible_player is None for r in ue),
        "low_sample": policy.count_flagged(games=games),
        "rallies": [r.number for r in ue],
    }

    own_faults = [r for r in served if r.ending == "fault" and r.actor == side]
    serve_faults = [r for r in own_faults if r.fault_kind == "serve"]
    untyped = sum(r.fault_kind is None for r in own_faults)
    an05 = proportion(len(serve_faults), [r.number for r in served], policy)
    an05["rallies"] = [r.number for r in serve_faults]
    an05["fault_type_not_tagged"] = untyped
    an05["low_sample"] = an05["low_sample"] or untyped > 0  # a lower bound (dictionary AN-05)
    out["AN-05"] = an05

    game_runs = _runs(counted, side)
    runs = [length for _, length in game_runs]
    histogram = dict.fromkeys(RUN_BUCKETS, 0)
    for length in runs:
        histogram["5+" if length >= 5 else str(length)] += 1
    out["AN-06"] = {
        "longest": max(runs, default=0),
        # dictionary AN-06: the longest run per side per game, games in scope in play order
        "longest_by_game": [
            max((n for g, n in game_runs if g == number), default=0) for number in game_numbers
        ],
        "histogram": histogram,
        "n": sum(runs),
        "low_sample": False,  # descriptive, never flagged (dictionary AN-06)
        "rallies": [r.number for r in counted if r.point_to == side],
    }

    ended = [r for r in counted if r.actor == side]
    counts = {c: sum(r.ending == c for r in ended) for c in CATEGORIES}
    shares = {}
    flagged = False
    for category, k in counts.items():
        p = proportion(k, [r.number for r in ended], policy)
        shares[category] = {key: p[key] for key in ("k", "value", "ci_low", "ci_high")}
        flagged = flagged or p["low_sample"]  # rule 0.3: n or any share's width (PE-R1-ST044-01)
    out["AN-07"] = {
        "n": len(ended),
        "counts": counts,
        "shares": shares,
        "low_sample": flagged,
        "rallies": [r.number for r in ended],
    }
    return out


def starter_stats(sheet: Mapping[str, Any], policy: LowSamplePolicy | None = None) -> Stats:
    """AN-01..AN-07 per side (A, B) for one match: ``stats[metric][side] -> fields``."""
    rules = policy or LowSamplePolicy()
    counted = counted_rallies(sheet)
    check_conservation(counted, attribute_lost_rallies(counted))  # FR-109, every computation
    games = game_numbers_in_scope(sheet)
    stats: Stats = {m: {} for m in METRICS}
    for side in SIDES:
        for metric, value in _side_stats(counted, side, games, rules).items():
            stats[metric][side] = value
    return stats
