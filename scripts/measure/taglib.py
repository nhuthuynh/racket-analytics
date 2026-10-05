"""Pure helpers for the Sprint 2 goal scorecard (docs/sprints/02/goal-scorecard.md).

Standard library only. Nothing here does I/O: `live_tagging.py` and `tag_latency.py` do the
network work and use these helpers to turn what they saw into numbers and differences.
Everything fails closed: no rows, no samples or a malformed body never reads as a pass
(ADR 0014). Tests: infra/tests/test_measure_sprint02.py.

The side-out stepper below is an **independent reference** written for the harness from the
QD §2.2 rows in sprint-01 §7.8 (PROVISIONAL-UNVERIFIED, ADR 0009, OQ-01 still open). It
derives the score calls the live journey expects. It is neither the product engine
(`racket.sports.pickleball.rules`) nor the QA oracle (`backend/tests/oracle/`), and it
imports neither. If the coach changes a provisional rule, this stepper and its tests change
with a test-change-request row, like every other provisional row.
"""

from __future__ import annotations

import copy
import json
import math
import random
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Any

SIDES = ("A", "B")
ENDINGS = ("winner", "unforced_error", "forced_error", "fault", "replay")
# Fields of one score-sheet row the harness compares (the api-sprint-02 contract names;
# tagcontract.py holds the mapping if the contract renames them).
ROW_FIELDS = (
    "number",
    "serving_side",
    "score_before",
    "score_after",
    "winning_side",
    "ending",
    "marker",
)
UNOFFICIAL_LABEL = "unofficial scoring (rules not yet verified)"  # FR-055, sprint-02 §3.1


class GameOver(Exception):
    """A rally was applied to a finished game (SOD-12)."""


@dataclass(frozen=True)
class DoublesState:
    score: dict[str, int]
    serving_side: str
    server_number: int
    winner: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def _other(side: str) -> str:
    return "B" if side == "A" else "A"


def new_doubles_game(first_serving_side: str) -> DoublesState:
    """0-0-2: the first-service exception of the provisional preset (SOD-01, SOD-02)."""
    if first_serving_side not in SIDES:
        raise ValueError(f"unknown side {first_serving_side!r}")
    return DoublesState(score={"A": 0, "B": 0}, serving_side=first_serving_side, server_number=2)


def step_doubles(
    state: DoublesState, winner: str, *, target: int = 11, margin: int = 2
) -> DoublesState:
    """One rally under provisional side-out doubles. ``winner`` is "A", "B" or "replay"."""
    if winner not in (*SIDES, "replay"):
        raise ValueError(f"unknown winner {winner!r}")
    if state.winner is not None:
        raise GameOver("game already over")
    if winner == "replay":
        return state
    srv = state.serving_side
    if winner == srv:
        score = dict(state.score)
        score[srv] += 1
        done = score[srv] >= target and score[srv] - score[_other(srv)] >= margin
        return replace(state, score=score, winner=srv if done else None)
    if state.server_number == 1:
        return replace(state, server_number=2)
    return replace(state, serving_side=_other(srv), server_number=1)


def call_doubles(state: DoublesState) -> str:
    """Three-number call, serving side first (FR-048, provisional format)."""
    srv = state.serving_side
    return f"{state.score[srv]}-{state.score[_other(srv)]}-{state.server_number}"


def _tag(winner: str | None, ending: str, player: str | None = None) -> dict[str, Any]:
    return {
        "winning_side": winner,
        "ending": ending,
        "responsible_player": player,
        "fault_kind": None,
    }


def with_times(tags: Sequence[dict[str, Any]], duration_ms: int = 60_000) -> list[dict[str, Any]]:
    """Spread the rallies over the video: integer ms, ordered, no overlap (I5, QD-TR-02)."""
    if not tags:
        return []
    step = duration_ms // len(tags)
    if step < 2:
        raise ValueError("video too short for this many rallies")
    out = []
    for i, tag in enumerate(tags):
        start = i * step
        out.append({**tag, "start_ms": start, "end_ms": start + step - 1})
    return out


# The demo / journey script: sprint-02 §12 steps 1-5 (6 rallies, doubles, side A serves first).
JOURNEY_TAGS: list[dict[str, Any]] = with_times(
    [
        _tag("A", "winner", "A1"),
        _tag("B", "unforced_error"),  # "player not tagged"
        _tag("A", "forced_error", "B1"),
        _tag("A", "fault", "B2"),
        _tag(None, "replay"),
        _tag("A", "winner"),
    ],
    duration_ms=48_000,
)

# C-02 (provisional): side A wins rallies 1-10 (10-0-2); rally 11 is a side-out; the game is
# won 11-0 at rally 14. Changing rally 11 to "won by A" ends the game at rally 11, and rallies
# 12-14 must be kept and marked "needs your decision", never deleted (FR-053).
CONFLICT_TAGS: list[dict[str, Any]] = with_times(
    [_tag("A", "winner")] * 10
    + [_tag("B", "winner"), _tag("A", "winner"), _tag("A", "winner"), _tag("A", "winner")],
    duration_ms=56_000,
)
CONFLICT_FLIP = 11


def with_winner(tags: Sequence[dict[str, Any]], *, rally: int, side: str) -> list[dict[str, Any]]:
    """A copy of ``tags`` with rally ``rally`` (1-based) won by ``side``."""
    if not 1 <= rally <= len(tags):
        raise ValueError(f"rally {rally} does not exist")
    out = copy.deepcopy(list(tags))
    out[rally - 1]["winning_side"] = side
    return out


def outcome_problems(tags: Sequence[dict[str, Any]]) -> list[str]:
    """Invariant I6 as the harness relies on it: a winner is credited to the winning side, an
    error or fault to the losing side (pending coach review, match-aggregate §8 Q2)."""
    problems = []
    for i, tag in enumerate(tags, start=1):
        ending, side, player = tag["ending"], tag["winning_side"], tag["responsible_player"]
        if ending not in ENDINGS:
            problems.append(f"rally {i}: unknown ending {ending!r}")
            continue
        if (ending == "replay") != (side is None):
            problems.append(f"rally {i}: replay must have no side, other endings one side")
            continue
        if player is None or side is None:
            continue
        on_winning = player[0] == side
        if ending == "winner" and not on_winning:
            problems.append(f"rally {i}: responsible player {player} is not on the winning side")
        if ending != "winner" and on_winning:
            problems.append(f"rally {i}: responsible player {player} is not on the losing side")
    return problems


def expected_rows(
    tags: Sequence[dict[str, Any]], *, first_serving_side: str, target: int = 11
) -> list[dict[str, Any]]:
    """The score-sheet rows the projection must produce for one game (match-aggregate §5)."""
    state = new_doubles_game(first_serving_side)
    rows = []
    for number, tag in enumerate(tags, start=1):
        row = {
            "number": number,
            "winning_side": tag["winning_side"],
            "ending": tag["ending"],
        }
        if state.winner is not None:
            row.update(
                serving_side=None, score_before=None, score_after=None, marker="needs_decision"
            )
        else:
            after = step_doubles(state, tag["winning_side"] or "replay", target=target)
            row.update(
                serving_side=state.serving_side,
                score_before=call_doubles(state),
                score_after=call_doubles(after),
                marker=None,
            )
            state = after
        rows.append(row)
    return rows


def game_winner(tags: Sequence[dict[str, Any]], first_serving_side: str) -> str | None:
    state = new_doubles_game(first_serving_side)
    for tag in tags:
        if state.winner is not None:
            break
        state = step_doubles(state, tag["winning_side"] or "replay")
    return state.winner


def three_game_script(
    seed: int, *, p_serving_wins: float = 0.6, cap: int = 400
) -> list[dict[str, Any]]:
    """A deterministic, fully decided best-of-3 doubles match for NFR-013 (IT-02-08 live).

    Every rally ends "winner" with no responsible player, so any later correction of a
    winning side is a valid command (I6)."""
    rng = random.Random(seed)  # noqa: S311 (deterministic fixture, not security)
    games, wins = [], {"A": 0, "B": 0}
    first = "A"
    while max(wins.values()) < 2:
        state, tags = new_doubles_game(first), []
        while state.winner is None:
            if len(tags) >= cap:
                raise ValueError("game did not end within the cap")
            srv = state.serving_side
            winner = srv if rng.random() < p_serving_wins else _other(srv)
            tags.append(_tag(winner, "winner"))
            state = step_doubles(state, winner)
        wins[state.winner] += 1
        games.append({"first_serving_side": first, "tags": tags})
        first = _other(first)
    return games


# ---------------------------------------------------------------- sheet comparison
def normalise_sheet(
    body: dict[str, Any], fields: Sequence[str] = ROW_FIELDS
) -> list[dict[str, Any]]:
    rows = body.get("rows") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        raise ValueError("score sheet body has no rows list")
    out = [{f: r.get(f) for f in fields} for r in rows]
    return sorted(out, key=lambda r: r["number"])


def compare_rows(expected: Sequence[dict[str, Any]], actual: Sequence[dict[str, Any]]) -> list[str]:
    if not expected and not actual:
        return ["no rows to compare"]
    diffs = []
    if len(expected) != len(actual):
        diffs.append(f"row count: expected {len(expected)}, got {len(actual)}")
    for exp, act in zip(expected, actual, strict=False):
        for f in ROW_FIELDS:
            if exp.get(f) != act.get(f):
                diffs.append(
                    f"rally {exp['number']} {f}: expected {exp.get(f)!r}, got {act.get(f)!r}"
                )
    return diffs


def _no_floats(obj: Any) -> None:
    if isinstance(obj, float):
        raise ValueError("float in canonical sheet (match-aggregate §5: no floats)")
    if isinstance(obj, dict):
        for v in obj.values():
            _no_floats(v)
    elif isinstance(obj, list):
        for v in obj:
            _no_floats(v)


def canonical_bytes(obj: Any) -> bytes:
    """Sorted keys, no spaces, no floats: the byte form the golden replay compares (NFR-075)."""
    _no_floats(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


# ---------------------------------------------------------------- media URLs (NFR-055)
def media_url_problems(
    url: str, ttl_s: float | None, session_value: str, *, max_ttl_s: int = 900
) -> list[str]:
    problems = []
    if ttl_s is None or ttl_s <= 0:
        problems.append("ttl missing or not positive")
    elif ttl_s > max_ttl_s:
        problems.append(f"ttl {ttl_s:g} s > {max_ttl_s} s")
    if not session_value:
        problems.append("no session value to check against")
    elif session_value in url:
        problems.append("session token in URL")
    if "racket_session" in url:
        problems.append("session cookie name in URL")
    return problems


# ---------------------------------------------------------------- timings
def _nearest_rank(samples: Sequence[float], p: float) -> float:
    ordered = sorted(samples)
    return ordered[max(1, math.ceil(p / 100 * len(ordered))) - 1]


def timing_summary(samples_ms: Sequence[float], *, max_p95_ms: float, min_n: int) -> dict[str, Any]:
    n = len(samples_ms)
    if n == 0:
        return {
            "n": 0,
            "p50_ms": None,
            "p95_ms": None,
            "max_ms": None,
            "target_p95_ms": max_p95_ms,
            "min_n": min_n,
            "ok": False,
        }
    p95 = _nearest_rank(samples_ms, 95)
    return {
        "n": n,
        "p50_ms": round(_nearest_rank(samples_ms, 50), 1),
        "p95_ms": round(p95, 1),
        "max_ms": round(max(samples_ms), 1),
        "target_p95_ms": max_p95_ms,
        "min_n": min_n,
        "ok": n >= min_n and p95 <= max_p95_ms,
    }
