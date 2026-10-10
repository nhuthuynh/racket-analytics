"""Pure helpers for the Sprint 3 goal scorecard (docs/sprints/03/goal-scorecard.md).

Standard library only, no I/O. `live_stats.py` and `stats_latency.py` do the network work and
use these helpers to turn what they saw into numbers and differences. Everything fails closed:
no metrics, no evidence items or no inventoried tables never reads as a pass (ADR 0014).
Tests: infra/tests/test_measure_sprint03.py.

**Independent reference.** The starter stats below are computed from Quick Tag inputs with
taglib's side-out stepper (PROVISIONAL-UNVERIFIED, ADR 0009), following the formulas of
docs/domain/metric-dictionary.md AN-01..AN-07 (v0.1, coach judgment). The tests pin them to the
coach's hand count in §2 of that file. This module is neither the product's analytics code
(`racket.analytics`) nor a QA oracle, and imports neither. When the coach changes a definition
(a dictionary version bump), this file and its tests change with a test-change-request row.

Rally references are match-wide 1-based sequence numbers over all games in order (one game:
the rally number). `statscontract.py` maps them to the API's evidence items.
"""

from __future__ import annotations

import math
import re
import uuid
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import taglib as t

Z95 = 1.959963984540054
MIN_PROPORTION_N = 20  # FR-101, ADR 0005 (config in the product)
MAX_INTERVAL_WIDTH = 0.30  # FR-101
MIN_GAMES = 2  # count metrics, FR-101
MIN_TURNS = 10  # AN-03
CATEGORIES = ("winner", "unforced_error", "forced_error", "fault")
METRICS = ("AN-01", "AN-02", "AN-03", "AN-04", "AN-05", "AN-06", "AN-07")
FLOAT_TOLERANCE = 1e-3
EVIDENCE_MAX = 10  # FR-103


def _tag(winner: str | None, ending: str, kind: str | None = None, player: str | None = None):
    return {
        "winning_side": winner,
        "ending": ending,
        "fault_kind": kind,
        "responsible_player": player,
    }


# The coach's worked example (metric-dictionary §2), the live journey's stats game. Every
# responsible player is on the side that made the ending (I6), so each tag is a valid command.
STATS_TAGS: list[dict[str, Any]] = t.with_times(
    [
        _tag("A", "winner", None, "A1"),
        _tag("B", "fault", "serve", "A2"),
        _tag("B", "winner"),
        _tag("B", "unforced_error", None, "A1"),
        _tag("A", "forced_error", None, "B2"),
        _tag("A", "fault", "nvz", "B1"),
        _tag("A", "winner", None, "A2"),
        _tag(None, "replay"),
        _tag("A", "unforced_error"),
        _tag("B", "unforced_error", None, "A2"),
        _tag("A", "fault"),
        _tag("B", "fault", "serve", "A1"),
        _tag("B", "winner", None, "B1"),
        _tag("B", "winner", None, "B2"),
    ],
    duration_ms=56_000,
)
CORRECTED_RALLY = 3  # "B winner, no player" -> "A winner": valid under I6


# ---------------------------------------------------------------- uncertainty (FR-101, ADR 0005)
def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float] | None:
    """95% Wilson score interval for k successes in n trials; None when n == 0."""
    if n < 0 or k < 0 or k > n:
        raise ValueError(f"impossible counts k={k}, n={n}")
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    low = 0.0 if k == 0 else max(0.0, centre - half)  # exact bounds at the edges
    high = 1.0 if k == n else min(1.0, centre + half)
    return low, high


def proportion_flag(k: int, n: int) -> bool:
    """Low sample: n below the minimum, or the interval wider than 30 points (FR-101)."""
    ci = wilson(k, n)
    if ci is None or n < MIN_PROPORTION_N:
        return True
    return ci[1] - ci[0] > MAX_INTERVAL_WIDTH


def count_flag(*, games: int) -> bool:
    return games < MIN_GAMES


# ---------------------------------------------------------------- reference replay
def _actor(tag: Mapping[str, Any]) -> str | None:
    """Rule 0.2: a winner is the winning side's; an error or fault is the losing side's."""
    side = tag["winning_side"]
    if tag["ending"] == "replay" or side is None:
        return None
    return side if tag["ending"] == "winner" else ("B" if side == "A" else "A")


def annotate(
    tags: Sequence[Mapping[str, Any]], *, first_serving_side: str, target: int = 11
) -> list[dict[str, Any]]:
    """One game of Quick Tag inputs → per-rally records with serve, score and point."""
    if not tags:
        raise ValueError("a game with no rallies")
    state = t.new_doubles_game(first_serving_side)
    out = []
    for number, tag in enumerate(tags, start=1):
        if tag.get("ending") not in t.ENDINGS:
            raise ValueError(f"rally {number}: unknown ending {tag.get('ending')!r}")
        rec: dict[str, Any] = {
            "number": number,
            "winning_side": tag["winning_side"],
            "ending": tag["ending"],
            "fault_kind": tag.get("fault_kind"),
            "responsible_player": tag.get("responsible_player"),
            "actor": _actor(tag),
        }
        if state.winner is not None:  # kept, "needs your decision": never counted
            rec.update(serving_side=None, server_number=None, score_before=None)
            rec.update(score_after=None, point_to=None, excluded=True)
            out.append(rec)
            continue
        after = t.step_doubles(state, tag["winning_side"] or "replay", target=target)
        point_to = next((x for x in t.SIDES if after.score[x] > state.score[x]), None)
        rec.update(
            serving_side=state.serving_side,
            server_number=state.server_number,
            score_before=dict(state.score),
            score_after=dict(after.score),
            point_to=point_to,
            excluded=tag["ending"] == "replay",
        )
        out.append(rec)
        state = after
    return out


def _records(games: Sequence[Mapping[str, Any]]) -> list[list[dict[str, Any]]]:
    if not games:
        raise ValueError("no games")
    out, offset = [], 0
    for g in games:
        recs = annotate(g["tags"], first_serving_side=g["first_serving_side"])
        for r in recs:
            r["ref"] = offset + r["number"]
        offset += len(recs)
        out.append(recs)
    return out


def _proportion(k: int, rallies: list[int]) -> dict[str, Any]:
    n = len(rallies)
    ci = wilson(k, n)
    return {
        "k": k,
        "n": n,
        "value": round(k / n, 4) if n else None,
        "ci_low": round(ci[0], 4) if ci else None,
        "ci_high": round(ci[1], 4) if ci else None,
        "low_sample": proportion_flag(k, n),
        "rallies": rallies,
    }


def _bucket(length: int) -> str:
    return "5+" if length >= 5 else str(length)


def starter_stats(games: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    """AN-01..AN-07 per side for one match (metric-dictionary §1, v0.1)."""
    per_game = _records(games)
    counted = [r for recs in per_game for r in recs if not r["excluded"]]
    n_games = len(per_game)
    stats: dict[str, dict[str, dict[str, Any]]] = {m: {} for m in METRICS}
    for side in t.SIDES:
        served = [r for r in counted if r["serving_side"] == side]
        received = [r for r in counted if r["serving_side"] != side]
        stats["AN-01"][side] = _proportion(
            sum(r["winning_side"] == side for r in served), [r["ref"] for r in served]
        )
        stats["AN-02"][side] = _proportion(
            sum(r["winning_side"] == side for r in received), [r["ref"] for r in received]
        )

        turns, points = 0, 0
        for recs in per_game:
            prev = None
            for r in recs:
                if r["excluded"]:
                    continue
                if r["serving_side"] == side and prev != side:
                    turns += 1
                prev = r["serving_side"]
                if r["serving_side"] == side and r["point_to"] == side:
                    points += 1
        stats["AN-03"][side] = {
            "points": points,
            "turns": turns,
            "value": round(points / turns, 1) if turns else None,
            "low_sample": turns < MIN_TURNS,
            "rallies": [r["ref"] for r in served if r["point_to"] == side],
        }

        ue = [r for r in counted if r["ending"] == "unforced_error" and r["actor"] == side]
        by_player = Counter(r["responsible_player"] for r in ue if r["responsible_player"])
        stats["AN-04"][side] = {
            "count": len(ue),
            "games": n_games,
            "value": round(len(ue) / n_games, 1),
            "by_player": dict(sorted(by_player.items())),
            "player_not_tagged": sum(r["responsible_player"] is None for r in ue),
            "low_sample": count_flag(games=n_games),
            "rallies": [r["ref"] for r in ue],
        }

        own_faults = [r for r in served if r["ending"] == "fault" and r["actor"] == side]
        serve_faults = [r for r in own_faults if r["fault_kind"] == "serve"]
        untyped = sum(r["fault_kind"] is None for r in own_faults)
        an05 = _proportion(len(serve_faults), [r["ref"] for r in served])
        an05["rallies"] = [r["ref"] for r in serve_faults]
        an05["fault_type_not_tagged"] = untyped
        an05["low_sample"] = an05["low_sample"] or untyped > 0
        stats["AN-05"][side] = an05

        runs: list[int] = []
        longest_by_game: list[int] = []  # dictionary AN-06: per side per game, play order
        for recs in per_game:
            game_runs: list[int] = []
            run_side, length = None, 0
            for r in recs:
                if r["excluded"] or r["point_to"] is None:
                    continue
                if r["point_to"] == run_side:
                    length += 1
                    continue
                if run_side == side:
                    game_runs.append(length)
                run_side, length = r["point_to"], 1
            if run_side == side:
                game_runs.append(length)
            runs.extend(game_runs)
            longest_by_game.append(max(game_runs, default=0))
        hist = dict.fromkeys(("1", "2", "3", "4", "5+"), 0)
        for length in runs:
            hist[_bucket(length)] += 1
        stats["AN-06"][side] = {
            "longest": max(runs, default=0),
            "longest_by_game": longest_by_game,
            "histogram": hist,
            "n": sum(runs),
            "low_sample": False,
            "rallies": [r["ref"] for r in counted if r["point_to"] == side],
        }

        ended = [r for r in counted if r["actor"] == side]
        counts = {c: sum(r["ending"] == c for r in ended) for c in CATEGORIES}
        stats["AN-07"][side] = {
            "n": len(ended),
            "counts": counts,
            # rule 0.3 on each of the four shares: n < 20 or any interval wider than 30 points
            "low_sample": any(proportion_flag(k, len(ended)) for k in counts.values()),
            "rallies": [r["ref"] for r in ended],
        }
    return stats


# ---------------------------------------------------------------- FR-109 attribution conservation
def lost_rallies(games: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, list[int]]]:
    counted = [r for recs in _records(games) for r in recs if not r["excluded"]]
    out: dict[str, dict[str, list[int]]] = {}
    for side in t.SIDES:
        lost = [r for r in counted if r["winning_side"] not in (None, side)]
        out[side] = {
            "serve": [r["ref"] for r in lost if r["serving_side"] == side],
            "receive": [r["ref"] for r in lost if r["serving_side"] != side],
        }
    return out


def attribution_problems(
    lost: Mapping[str, Mapping[str, Sequence[int]]],
    attributed: Mapping[str, Mapping[str, Sequence[int]]],
) -> list[str]:
    """Every lost rally is attributed exactly once (categories plus "unattributed")."""
    problems = []
    for side, phases in lost.items():
        for phase, refs in phases.items():
            got = Counter(attributed.get(side, {}).get(phase, []))
            want = Counter(refs)
            if got != want:
                problems.append(
                    f"{side} {phase}: lost {sorted(want.elements())}, "
                    f"attributed {sorted(got.elements())}"
                )
    return problems


def conservation_problems(games: Sequence[Mapping[str, Any]]) -> list[str]:
    """The reference attribution: each lost rally goes to its ending category once."""
    lost = lost_rallies(games)
    reference = {s: {p: list(v) for p, v in ph.items()} for s, ph in lost.items()}
    return attribution_problems(lost, reference)


# ---------------------------------------------------------------- comparison with the API
COMPARED = {
    "AN-01": ("k", "n", "value", "ci_low", "ci_high", "low_sample"),
    "AN-02": ("k", "n", "value", "ci_low", "ci_high", "low_sample"),
    "AN-03": ("points", "turns", "value", "low_sample"),
    "AN-04": ("count", "games", "value", "by_player", "player_not_tagged", "low_sample"),
    "AN-05": ("k", "n", "value", "ci_low", "ci_high", "fault_type_not_tagged", "low_sample"),
    "AN-06": ("longest", "longest_by_game", "histogram", "n", "low_sample"),
    "AN-07": ("n", "counts", "low_sample"),
}


def as_api_shape(stats: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> dict[str, Any]:
    """The reference in the assumed response shape (statscontract.py names the real one)."""
    return {
        "metrics": {
            m: {side: {k: v[k] for k in COMPARED[m]} for side, v in stats[m].items()}
            for m in METRICS
        }
    }


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and abs(float(a) - float(b)) <= FLOAT_TOLERANCE
    return a == b


def compare_stats(expected: Mapping[str, Any], actual_body: Mapping[str, Any]) -> list[str]:
    metrics = actual_body.get("metrics") if isinstance(actual_body, Mapping) else None
    if not metrics:
        return ["no metrics in the response"]
    diffs = []
    for m in METRICS:
        if m not in metrics:
            diffs.append(f"{m} missing")
            continue
        for side in t.SIDES:
            got = metrics[m].get(side)
            if not isinstance(got, Mapping):
                diffs.append(f"{m} {side} missing")
                continue
            for key in COMPARED[m]:
                want = expected[m][side][key]
                if not _same(want, got.get(key)):
                    diffs.append(f"{m} {side} {key}: expected {want!r}, got {got.get(key)!r}")
    return diffs


def evidence_problems(body: Mapping[str, Any], expected_refs: Sequence[int]) -> list[str]:
    """FR-103: up to 10 rallies of the metric, with "see all n" (total = n)."""
    items = body.get("items") if isinstance(body, Mapping) else None
    if not isinstance(items, list):
        return ["evidence body has no items list"]
    problems = []
    want = set(expected_refs)
    if body.get("total") != len(expected_refs):
        problems.append(f"total {body.get('total')!r} != n {len(expected_refs)}")
    if len(items) > EVIDENCE_MAX:
        problems.append(f"more than {EVIDENCE_MAX} items ({len(items)})")
    if len(items) != min(EVIDENCE_MAX, len(expected_refs)):
        problems.append(f"{len(items)} items, expected {min(EVIDENCE_MAX, len(expected_refs))}")
    seen: set[int] = set()
    for item in items:
        ref = item.get("number") if isinstance(item, Mapping) else None
        if ref not in want:
            problems.append(f"rally {ref} is not behind this metric")
        if ref in seen:
            problems.append(f"rally {ref} listed twice")
        seen.add(ref)
    return problems


# ---------------------------------------------------------------- purge inventory (NFR-066 b)
_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")
ID_COLUMNS = ("match_id", "owner_id", "account_id")
ROOT_TABLES = (("matches", "id"), ("accounts", "id"))


def columns_sql(columns: Iterable[str] = ID_COLUMNS) -> str:
    """Every public table column that can hold a match or account id (psql -At -F'|')."""
    cols = list(columns)
    for c in cols:
        if not _IDENT.match(c):
            raise ValueError(f"unsafe identifier {c!r}")
    listed = ", ".join(f"'{c}'" for c in cols)
    # identifiers checked against _IDENT above
    return (
        "SELECT table_name, column_name FROM information_schema.columns "  # noqa: S608
        f"WHERE table_schema = 'public' AND column_name IN ({listed}) ORDER BY 1, 2;"
    )


def count_sql(pairs: Sequence[tuple[str, str]], ids: Sequence[str]) -> str:
    if not pairs:
        raise ValueError("no tables to inventory")
    if not ids:
        raise ValueError("no ids to look for")
    clean = []
    for raw in ids:
        try:
            clean.append(str(uuid.UUID(raw)))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError(f"not a uuid: {raw!r}") from exc
    in_list = ", ".join(f"'{i}'" for i in clean)
    parts = []
    for table, column in pairs:
        if not (_IDENT.match(table) and _IDENT.match(column)):
            raise ValueError(f"unsafe identifier {table!r}.{column!r}")
        # identifiers checked against _IDENT; ids parsed as UUIDs
        parts.append(
            f"SELECT '{table}.{column}' AS k, count(*) AS n FROM \"{table}\" "  # noqa: S608
            f'WHERE "{column}"::text IN ({in_list})'
        )
    return " UNION ALL ".join(parts) + ";"


def parse_pairs(out: str) -> list[tuple[str, str]]:
    pairs = []
    for line in out.splitlines():
        if not line.strip():
            continue
        cells = line.split("|")
        if len(cells) != 2:
            raise ValueError(f"not a table|column line: {line!r}")
        pairs.append((cells[0].strip(), cells[1].strip()))
    return pairs


def parse_counts(out: str) -> dict[str, int]:
    counts = {}
    for line in out.splitlines():
        if not line.strip():
            continue
        cells = line.split("|")
        if len(cells) != 2 or not cells[1].strip().isdigit():
            raise ValueError(f"not a key|count line: {line!r}")
        counts[cells[0].strip()] = int(cells[1])
    return counts


def purge_problems(counts: Mapping[str, int]) -> list[str]:
    if not counts:
        return ["no tables inventoried"]
    return [f"{k}: {n} rows left" for k, n in sorted(counts.items()) if n]
