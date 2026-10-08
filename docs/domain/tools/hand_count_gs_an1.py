"""QD-AN-03 hand count of the golden matches GS-AN-1 (COACH-1, pickleball-domain-coach).

GS-AN-1 v2 changed no script, so this count covers v1 and v2; the record is written for v2's
compared fields (scripts/measure/statslib.py COMPARED), incl. AN-06 ``longest_by_game``.

Documentation tooling only, not product code. It is written from the definitions in
docs/domain/metric-dictionary.md v0.1 (rules 0.1-0.6 and AN-01..AN-07) and does **not** import
the product (`racket.analytics`) or the QA reference (`scripts/measure/statslib.py`), so a
mistake shared by those two is not copied here. It replays each tag script rally by rally
under the PROVISIONAL-UNVERIFIED side-out doubles assumptions (rules-verified.md §5 rows 2-3:
game to 11, win by 2, start "0-0-2", server 1 then server 2, then side-out; all UNVERIFIED),
prints a trace a person can follow with a pencil, and writes the count in the shape that
backend/tests/regression/test_golden_an.py reads.

Run:   python3 docs/domain/tools/hand_count_gs_an1.py            # trace + summary
       python3 docs/domain/tools/hand_count_gs_an1.py --write    # also writes the record
"""

from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SET_DIR = REPO / "backend" / "tests" / "regression" / "golden_matches"
OUT = REPO / "docs" / "domain" / "hand-counts" / "GS-AN-1-v1.json"
MATCHES = ("gm1-two-games", "gm2-three-games", "gm3-corrections-needs-decision")
TARGET, MARGIN = 11, 2  # provisional preset, UNVERIFIED
MIN_N, MAX_WIDTH, MIN_GAMES, MIN_TURNS = 20, 0.30, 2, 10  # ADR 0005 / FR-101 / AN-03
Z = 1.959963984540054
CATS = ("winner", "unforced_error", "forced_error", "fault")


def other(side: str) -> str:
    return "B" if side == "A" else "A"


def wilson(k: int, n: int) -> tuple[float, float]:
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def flagged(k: int, n: int) -> bool:
    """Rule 0.3: n below min_sample, or the 95% interval wider than 30 points."""
    if n < MIN_N:
        return True
    lo, hi = wilson(k, n)
    return hi - lo > MAX_WIDTH


def proportion(k: int, n: int, rallies: list[int]) -> dict:
    lo, hi = wilson(k, n) if n else (None, None)
    return {
        "k": k,
        "n": n,
        "value": round(k / n, 4) if n else None,
        "ci_low": round(lo, 4) if n else None,
        "ci_high": round(hi, 4) if n else None,
        "low_sample": True if n == 0 else flagged(k, n),
        "rallies": rallies,
    }


def replay_game(tags: list[dict], first: str, offset: int, trace: list[str]) -> list[dict]:
    """One game: serve, server number and score before each rally; who scored."""
    server, number = first, 2  # first-service exception: "0-0-2"
    score = {"A": 0, "B": 0}
    over = False
    rows = []
    for i, tag in enumerate(tags, start=1):
        ref = offset + i
        win, ending = tag["winning_side"], tag["ending"]
        actor = None
        if ending != "replay" and win is not None:
            actor = win if ending == "winner" else other(win)  # rule 0.2
        row = {"ref": ref, "win": win, "ending": ending, "kind": tag.get("fault_kind"),
               "player": tag.get("responsible_player"), "actor": actor, "server": server,
               "number": number, "point": None, "counted": False, "turn_start": False}
        call = f"{score[server]}-{score[other(server)]}-{number} {server}"
        if over:
            trace.append(f"  {ref:>3} {call:<10} {win} {ending:<15} needs decision: excluded")
            row["server"] = None
            rows.append(row)
            continue
        if ending == "replay":
            trace.append(f"  {ref:>3} {call:<10} -  replay          excluded")
            rows.append(row)
            continue
        row["counted"] = True
        if win == server:
            score[server] += 1
            row["point"] = server
        elif number == 1:
            number = 2
        else:
            server, number = other(server), 1
        a, b = score["A"], score["B"]
        if max(a, b) >= TARGET and abs(a - b) >= MARGIN:
            over = True
        after = f"{score[server]}-{score[other(server)]}-{number} {server}"
        trace.append(f"  {ref:>3} {call:<10} {win} {ending:<15} -> {after}"
                     + ("  GAME" if over else ""))
        rows.append(row)
    return rows


def count(script: dict, trace: list[str]) -> tuple[dict, dict]:
    games = copy.deepcopy(script["games"])
    flat = [t for g in games for t in g["tags"]]
    for c in script["corrections"]:
        trace.append(f"  correction: rally {c['rally']} {c['field']} -> {c['value']}")
        flat[c["rally"] - 1][c["field"]] = c["value"]
    per_game, offset = [], 0
    for gi, g in enumerate(games, start=1):
        trace.append(f" game {gi}, {g['first_serving_side']} serves first")
        per_game.append(replay_game(g["tags"], g["first_serving_side"], offset, trace))
        offset += len(g["tags"])
    rows = [r for g in per_game for r in g if r["counted"]]
    n_games = len(per_game)
    out: dict = {m: {} for m in ("AN-01", "AN-02", "AN-03", "AN-04", "AN-05", "AN-06", "AN-07")}
    extra: dict = {}
    for s in "AB":
        served = [r for r in rows if r["server"] == s]
        recv = [r for r in rows if r["server"] == other(s)]
        out["AN-01"][s] = proportion(sum(r["win"] == s for r in served), len(served),
                                     [r["ref"] for r in served])
        out["AN-02"][s] = proportion(sum(r["win"] == s for r in recv), len(recv),
                                     [r["ref"] for r in recv])
        # AN-03: a service turn starts when S gains the serve or at the game start.
        turns = 0
        for g in per_game:
            prev = None
            for r in g:
                if not r["counted"]:
                    continue
                if r["server"] == s and prev != s:
                    turns += 1
                prev = r["server"]
        pts = [r["ref"] for r in served if r["point"] == s]
        out["AN-03"][s] = {"points": len(pts), "turns": turns,
                           "value": round(len(pts) / turns, 1) if turns else None,
                           "low_sample": turns < MIN_TURNS, "rallies": pts}
        ue = [r for r in rows if r["ending"] == "unforced_error" and r["actor"] == s]
        by: dict[str, int] = {}
        for r in ue:
            if r["player"]:
                by[r["player"]] = by.get(r["player"], 0) + 1
        out["AN-04"][s] = {"count": len(ue), "games": n_games,
                           "value": round(len(ue) / n_games, 1),
                           "by_player": dict(sorted(by.items())),
                           "player_not_tagged": sum(r["player"] is None for r in ue),
                           "low_sample": n_games < MIN_GAMES, "rallies": [r["ref"] for r in ue]}
        own = [r for r in served if r["ending"] == "fault" and r["actor"] == s]
        sf = [r["ref"] for r in own if r["kind"] == "serve"]
        untyped = sum(r["kind"] is None for r in own)
        an05 = proportion(len(sf), len(served), sf)
        an05["fault_type_not_tagged"] = untyped
        an05["low_sample"] = an05["low_sample"] or untyped > 0  # AN-05 edge case
        out["AN-05"][s] = an05
        # AN-06: maximal runs of points; serve-only rallies do not break a run; reset per game.
        runs, by_game = [], []
        for g in per_game:
            mine, cur_side, cur = [], None, 0
            for r in g:
                if not r["counted"] or r["point"] is None:
                    continue
                if r["point"] == cur_side:
                    cur += 1
                else:
                    if cur_side == s:
                        mine.append(cur)
                    cur_side, cur = r["point"], 1
            if cur_side == s:
                mine.append(cur)
            runs += mine
            by_game.append(max(mine, default=0))
        hist = {"1": 0, "2": 0, "3": 0, "4": 0, "5+": 0}
        for x in runs:
            hist["5+" if x >= 5 else str(x)] += 1
        # longest_by_game is a compared field since GS-AN-1 v2 (statslib.COMPARED, ST-049).
        out["AN-06"][s] = {"longest": max(runs, default=0), "longest_by_game": by_game,
                           "histogram": hist, "n": sum(runs), "low_sample": False,
                           "rallies": [r["ref"] for r in rows if r["point"] == s]}
        extra[s] = {}
        ended = [r for r in rows if r["actor"] == s]
        counts = {c: sum(r["ending"] == c for r in ended) for c in CATS}
        n = len(ended)
        # Rule 0.3 applies to each of the four shares (AN-07 unit: % per category, Wilson each).
        out["AN-07"][s] = {"n": n, "counts": counts,
                           "low_sample": n < MIN_N or any(flagged(counts[c], n) for c in CATS),
                           "rallies": [r["ref"] for r in ended]}
        extra[s]["AN-07 low_sample by n only"] = n < MIN_N
    return out, extra


def main() -> None:
    record = {"by": "pickleball-domain-coach", "date": "2026-10-08",
              "method": "QD-AN-03 hand count from metric-dictionary.md v0.1, traced rally by "
                        "rally with docs/domain/tools/hand_count_gs_an1.py (independent of the "
                        "product and of statslib); PROVISIONAL-UNVERIFIED preset",
              "gold_set": "GS-AN-1", "gold_set_version": 2, "metric_dict_version": "0.1",
              "matches": {}, "not_compared": {}}
    for m in MATCHES:
        script = json.loads((SET_DIR / f"{m}.script.json").read_text())
        trace: list[str] = [m]
        metrics, extra = count(script, trace)
        print("\n".join(trace))
        for metric, sides in metrics.items():
            print(f"  {metric}: " + "; ".join(
                f"{s} " + ", ".join(f"{k}={v}" for k, v in vals.items() if k != "rallies")
                for s, vals in sides.items()))
        print(f"  extra: {extra}")
        record["matches"][m] = metrics
        record["not_compared"][m] = extra
    if "--write" in sys.argv:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(record, indent=2) + "\n")
        print(f"wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
