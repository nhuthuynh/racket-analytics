"""COACH-6b pattern check: the pattern catalogue against its own examples and GS-PAT-1.

Documentation tooling only, not product code (pickleball-domain-coach). It counts AN-09 (third-shot
drop share), AN-10 (third-shot drop success), AN-08 (return depth; AN-08S serve depth) and AN-13
(dink tolerance) straight from the text of docs/domain/pattern-catalogue.md v0.1 (§0-§5), over
Full Tag label documents (full-tag-labels/v1), per side. It imports neither the product
(`racket.analytics`) nor `scripts/measure/`: it is the coach's own replay, written from the
definitions, so that product = hand count = this replay can be shown (ADR 0044).

Checks (`--check`; each mismatch is one `DIFF` line, rc 1 unless there are 0):
1. every worked label example (`<!-- example: ID -->` + json block + `<!-- expect: {...} -->`)
   gives the expected fields;
2. every `<!-- wilson: k n lo hi -->` and `<!-- median: [xs] m l=L:[a,b] | none -->` figure;
3. the GS-PAT-1 fixture docs/domain/hand-counts/GS-PAT-1-v1.json: the replay equals the coach's
   hand count recorded in it (`counts`), rally by rally;
4. each GS-PAT-1 table of the catalogue (`<!-- table: GS-PAT-1 <id> -->`) holds exactly the rows
   printed here; a missing table is named.

Run:   python3 docs/domain/tools/pattern_example.py            # print the GS-PAT-1 tables
       python3 docs/domain/tools/pattern_example.py --check    # 0 differences or rc 1
"""

from __future__ import annotations

import json
import math
import re
import sys
from itertools import pairwise
from pathlib import Path
from typing import Any

Json = dict[str, Any]

REPO = Path(__file__).resolve().parents[3]
CATALOGUE = REPO / "docs" / "domain" / "pattern-catalogue.md"
FIXTURE = REPO / "docs" / "domain" / "hand-counts" / "GS-PAT-1-v1.json"

# §0.7 court frame (UNVERIFIED until P7): side A's half 0 <= y <= NET, side B's NET <= y <= LENGTH.
WIDTH, LENGTH, NET, NVZ = 6.10, 13.41, 6.705, 2.13
DEEP = 4.47  # AN-08: two thirds of the half (FR-171.R7)
MIN_N = {"AN-09": 20, "AN-10": 20, "AN-08": 20, "AN-08S": 20, "AN-13": 10}
Z95 = 1.959963984540054
TABLES = ("AN-09", "AN-13", "AN-08", "unassigned")


# ------------------------------------------------------------ geometry (§0.7)
def other(side: str) -> str:
    return "B" if side == "A" else "A"


def in_half(xy: list[float], side: str) -> bool:
    x, y = xy
    if not 0 <= x <= WIDTH:
        return False
    return 0 <= y <= NET if side == "A" else NET <= y <= LENGTH


def dist(xy: list[float]) -> float:
    return abs(xy[1] - NET)


# ------------------------------------------------------------------- rally reading (§0.1)
def hits(rally: Json) -> list[Json]:
    return [e for e in rally["events"] if e["type"] == "hit"]


def side_of(hit: Json) -> str:
    return str(hit["hitter"])[0]


def traj(hit: Json) -> str | None:
    value = hit.get("facets", {}).get("trajectory")
    return None if value is None else str(value)


def alternates(hs: list[Json]) -> bool:
    first = hs[:3]
    return all(side_of(a) != side_of(b) for a, b in pairwise(first))


def bounce_after(rally: Json, n: int) -> Json | None:
    """First bounce after hit n (1-based), before hit n+1 or the rally end."""
    seen = 0
    for e in rally["events"]:
        if e["type"] == "hit":
            seen += 1
            if seen > n:
                return None
        elif seen == n:
            bounce: Json = e
            return bounce
    return None


def lost_by(rally: Json, side: str) -> bool:
    return bool(rally["outcome"]["winning_side"] == other(side))


def unassigned(rally: Json) -> str | None:
    if rally["outcome"]["ending"] == "replay":
        return "replay"
    return None if hits(rally) else "no_serve_hit"


class Tally:
    """One pattern for one side: counted rallies, k-rallies, exclusions by reason."""

    def __init__(self) -> None:
        self.k: list[str] = []
        self.n: list[str] = []
        self.excluded: dict[str, list[str]] = {}
        self.mix: dict[str, list[str]] = {}
        self.runs: list[tuple[str, int]] = []
        self.censored: list[str] = []

    def exclude(self, reason: str, rid: str) -> None:
        self.excluded.setdefault(reason, []).append(rid)


# ------------------------------------------------------------ patterns (§2-§5)
def an09(doc: Json, s: str) -> Tally:
    t = Tally()
    for r in doc["rallies"]:
        hs = hits(r)
        if unassigned(r) or side_of(hs[0]) != s:
            continue
        if len(hs) < 3:
            t.exclude("no_third_shot", r["id"])
        elif not alternates(hs):
            t.exclude("side_order_invalid", r["id"])
        elif (third := traj(hs[2])) is None:
            t.exclude("facet_missing", r["id"])
        else:
            t.n.append(r["id"])
            t.mix.setdefault(third, []).append(r["id"])
            if third == "drop":
                t.k.append(r["id"])
    return t


def is_attack(hit: Json | None) -> bool | None:
    """§3: True attack, False decidedly not (absent, or both facets labelled non-attack)."""
    if hit is None:
        return False
    f = hit.get("facets", {})
    if f.get("trajectory") == "drive" or f.get("intent") == "speed_up":
        return True
    return False if "trajectory" in f and "intent" in f else None


def an10(doc: Json, s: str) -> Tally:
    t = Tally()
    drops = set(an09(doc, s).k)
    for r in doc["rallies"]:
        if r["id"] not in drops:
            continue
        hs = hits(r)
        if len(hs) <= 5 and lost_by(r, s):
            t.n.append(r["id"])  # (b) fails: lost at or before hit 5
            continue
        b = bounce_after(r, 3)
        xy = b.get("court_xy_m") if b else None
        in_nvz = xy is not None and in_half(xy, other(s)) and dist(xy) <= NVZ
        attack = is_attack(hs[3] if len(hs) > 3 else None)
        if in_nvz or attack is False:
            t.n.append(r["id"])
            t.k.append(r["id"])
        elif xy is not None and attack is True:
            t.n.append(r["id"])
        else:
            t.exclude("next_shot_unlabelled", r["id"])
    return t


def an08(doc: Json, s: str, serve: bool = False) -> Tally:
    """Return depth of returner s (AN-08), or serve depth of server s (AN-08S)."""
    t = Tally()
    shot = 1 if serve else 2
    for r in doc["rallies"]:
        hs = hits(r)
        if unassigned(r) or side_of(hs[0]) != (s if serve else other(s)):
            continue
        if len(hs) < shot:
            t.exclude("no_return", r["id"])
            continue
        if not alternates(hs):
            t.exclude("side_order_invalid", r["id"])
            continue
        b = bounce_after(r, shot)
        xy = b.get("court_xy_m") if b else None
        target = other(s)  # the server's half for a return, the receiving half for a serve
        if xy is None:
            t.exclude("bounce_missing", r["id"])
        elif not in_half(xy, target) or (serve and dist(xy) <= NVZ):
            t.exclude("not_in_play", r["id"])
        else:
            t.n.append(r["id"])
            if dist(xy) >= DEEP:
                t.k.append(r["id"])
    return t


def dink_run(hs: list[Json]) -> list[Json]:
    """Last maximal run of consecutive rally shots (hit 3+) with trajectory dink."""
    run: list[Json] = []
    best: list[Json] = []
    for h in hs[2:]:
        run = [*run, h] if traj(h) == "dink" else []
        if len(run) >= 2:
            best = run
    return best


def an13(doc: Json, s: str) -> Tally:
    t = Tally()
    for r in doc["rallies"]:
        hs = hits(r)
        if unassigned(r) or len(hs) < 4:
            continue
        if any(traj(h) is None for h in hs[2:]):
            t.exclude("facet_missing", r["id"])
            continue
        run = dink_run(hs)
        if not run:
            t.exclude("no_dink_exchange", r["id"])
            continue
        last = run[-1]
        erred = r["outcome"]["ending"] in ("unforced_error", "forced_error", "fault")
        if last is hs[-1] and side_of(last) == s and lost_by(r, s) and erred:
            t.runs.append((r["id"], sum(side_of(h) == s for h in run) - 1))
        else:
            t.censored.append(r["id"])
    return t


# ------------------------------------------------------------ uncertainty (§0.3)
def wilson(k: int, n: int) -> tuple[float, float]:
    p, z2 = k / n, Z95 * Z95
    centre = (p + z2 / (2 * n)) / (1 + z2 / n)
    half = Z95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def median(xs: list[int]) -> float:
    ys, n = sorted(xs), len(xs)
    return ys[n // 2] if n % 2 else (ys[n // 2 - 1] + ys[n // 2]) / 2


def order_l(n: int) -> int | None:
    """Largest l with P(Binomial(n, 0.5) <= l-1) <= 0.025; None below n = 6."""
    if n < 6:
        return None
    best, cdf = None, 0.0
    for rank in range(1, n + 1):
        cdf += math.comb(n, rank - 1) / 2**n
        if cdf > 0.025:
            break
        best = rank
    return best


def num(v: float) -> str:
    return f"{v:g}"


# ------------------------------------------------------------ check 1: examples
def measure(doc: Json, key: str) -> Json:
    pattern, s = key.split("@")
    fn = {"AN-09": an09, "AN-10": an10, "AN-08": an08, "AN-13": an13}
    t = an08(doc, s, serve=True) if pattern == "AN-08S" else fn[pattern](doc, s)
    out: Json = {"k": len(t.k), "n": len(t.n) if pattern != "AN-13" else len(t.runs)}
    out["excluded"] = {r: len(ids) for r, ids in t.excluded.items()}
    out["mix"] = {m: len(ids) for m, ids in t.mix.items()}
    out["runs"] = sorted(x for _, x in t.runs)
    out["n_censored"] = len(t.censored)
    un: dict[str, int] = {}
    for r in doc["rallies"]:
        if reason := unassigned(r):
            un[reason] = un.get(reason, 0) + 1
    out["unassigned"] = un
    return out


EXAMPLE = re.compile(
    r"<!-- example: (?P<id>\S+) -->\s*```json\n(?P<doc>.*?)```\s*<!-- expect: (?P<expect>.*?) -->",
    re.S,
)


def example_diffs(text: str) -> tuple[int, list[str]]:
    out, seen = [], 0
    for m in EXAMPLE.finditer(text):
        doc, expect = json.loads(m["doc"]), json.loads(m["expect"])
        for key, fields in expect.items():
            got = measure(doc, key)
            for f, want in fields.items():
                seen += 1
                if got[f] != want:
                    out.append(f"example {m['id']} {key} {f}: expected {want}, replay {got[f]}")
    return seen, out


def figure_diffs(text: str) -> tuple[int, list[str]]:
    out, seen = [], 0
    for k, n, lo, hi in re.findall(r"<!-- wilson: (\d+) (\d+) ([\d.]+) ([\d.]+) -->", text):
        seen += 1
        got = tuple(f"{v:.3f}" for v in wilson(int(k), int(n)))
        if got != (lo, hi):
            out.append(f"wilson {k}/{n}: stated {lo}-{hi}, computed {got[0]}-{got[1]}")
    for xs, m, rest in re.findall(r"<!-- median: (\[[^\]]*\]) (\S+) (\S+) -->", text):
        seen += 1
        values = json.loads(xs)
        ys, rank = sorted(values), order_l(len(values))
        iv = "none" if rank is None else f"l={rank}:[{ys[rank - 1]},{ys[len(ys) - rank]}]"
        if (num(median(values)), iv) != (m, rest):
            out.append(f"median {xs}: stated {m} {rest}, computed {num(median(values))} {iv}")
    return seen, out


# ------------------------------------------------------------ GS-PAT-1 replay
def replay(doc: Json) -> Json:
    """Same shape as `counts` in GS-PAT-1-v1.json (rally ids per bucket)."""
    out: Json = {}
    for s in "AB":
        t9, t8, t13 = an09(doc, s), an08(doc, s), an13(doc, s)
        out.setdefault("AN-09", {})[s] = {
            "mix": t9.mix,
            "excluded": t9.excluded,
        }
        out.setdefault("AN-08", {})[s] = {
            "deep": t8.k,
            "not_deep": [r for r in t8.n if r not in t8.k],
            "excluded": t8.excluded,
        }
        out.setdefault("AN-13", {})[s] = {
            "samples": dict(t13.runs),
            "censored": t13.censored,
            "excluded": t13.excluded,
        }
    un: dict[str, list[str]] = {}
    for r in doc["rallies"]:
        if reason := unassigned(r):
            un.setdefault(reason, []).append(r["id"])
    out["unassigned"] = un
    return out


def canon(v: object) -> object:
    """Order-free comparison: id lists as sets, dicts key by key."""
    if isinstance(v, dict):
        return {k: canon(x) for k, x in v.items() if x not in ([], {})}
    if isinstance(v, list):
        return sorted(v)
    return v


def leaf_diffs(where: str, hand: object, got: object) -> list[str]:
    """One line per differing bucket, naming the rally ids only one side has."""
    if isinstance(hand, dict) and isinstance(got, dict):
        return [
            d
            for k in sorted(set(hand) | set(got))
            for d in leaf_diffs(f"{where} {k}", hand.get(k, []), got.get(k, []))
        ]
    if hand == got:
        return []
    if isinstance(hand, list) and isinstance(got, list):
        only_h = sorted(set(hand) - set(got))
        only_g = sorted(set(got) - set(hand))
        return [f"{where}: hand count only {only_h}, replay only {only_g}"]
    return [f"{where}: hand count {hand}, replay {got}"]


def count_diffs(fixture: Json) -> tuple[int, list[str]]:
    out, seen = [], 0
    for mid, match in fixture["matches"].items():
        got: Json = canon(replay(match["labels"]))  # type: ignore[assignment]
        hand: Json = canon(match["counts"])  # type: ignore[assignment]
        for pattern in sorted(set(got) | set(hand)):
            seen += 1
            where = f"GS-PAT-1 {mid} {pattern}"
            out += leaf_diffs(where, hand.get(pattern, {}), got.get(pattern, {}))
    return seen, out


def state(n: int, pattern: str) -> str:
    return "rankable" if n >= MIN_N[pattern] else "low_sample"


def reasons(ex: dict[str, list[str]]) -> str:
    return ", ".join(f"{r} {len(ids)}" for r, ids in sorted(ex.items())) or "none"


def tables(fixture: Json) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {t: [] for t in TABLES}
    for mid, match in fixture["matches"].items():
        doc = match["labels"]
        for s in "AB":
            t = an09(doc, s)
            k, n = len(t.k), len(t.n)
            lo, hi = wilson(k, n) if n else (0.0, 0.0)
            mix = ", ".join(f"{m} {len(ids)}" for m, ids in sorted(t.mix.items()))
            rows["AN-09"].append(
                f"| {mid} | {s} | {k} | {n} | {k / n:.3f} | {lo:.3f}-{hi:.3f} | "
                f"{state(n, 'AN-09')} | {reasons(t.excluded)} | {mix} |"
            )
        for s in "AB":
            t = an13(doc, s)
            xs = sorted(x for _, x in t.runs)
            n, rank = len(xs), order_l(len(xs))
            iv = "none" if rank is None else f"[{xs[rank - 1]}, {xs[n - rank]}] (l = {rank})"
            rows["AN-13"].append(
                f"| {mid} | {s} | {', '.join(map(str, xs))} | {n} | {num(median(xs))} | {iv} | "
                f"{state(n, 'AN-13')} | {len(t.censored)} | {reasons(t.excluded)} |"
            )
        for s in "AB":
            t = an08(doc, s)
            k, n = len(t.k), len(t.n)
            lo, hi = wilson(k, n)
            rows["AN-08"].append(
                f"| {mid} | {s} | {k} | {n} | {k / n:.3f} | {lo:.3f}-{hi:.3f} | "
                f"{state(n, 'AN-08')} | {reasons(t.excluded)} |"
            )
        un = replay(doc)["unassigned"]
        fmt = "doubles" if len(doc["players"]) == 4 else "singles"
        rows["unassigned"].append(f"| {mid} | {fmt} | {len(doc['rallies'])} | {reasons(un)} |")
    return rows


def table_diffs(text: str, rows: dict[str, list[str]]) -> tuple[int, list[str]]:
    out, seen = [], 0
    lines = text.splitlines()
    for name, want in rows.items():
        marker = f"<!-- table: GS-PAT-1 {name} -->"
        seen += 1
        if marker not in lines:
            out.append(f"MISSING table GS-PAT-1 {name} in {CATALOGUE.relative_to(REPO)}")
            continue
        start = lines.index(marker) + 1
        body = []
        for ln in lines[start:]:
            if ln.startswith("|"):
                body.append(ln)
            elif body:
                break
        have = body[2:]  # skip header and separator
        for r in want:
            if r not in have:
                out.append(f"table GS-PAT-1 {name}: missing row {r}")
        for r in have:
            if r not in want:
                out.append(f"table GS-PAT-1 {name}: unexpected row {r}")
    return seen, out


# ------------------------------------------------------------ main
def main() -> int:
    text = CATALOGUE.read_text()
    fixture = json.loads(FIXTURE.read_text()) if FIXTURE.exists() else None
    if "--check" not in sys.argv:
        if fixture is None:
            print(f"no fixture {FIXTURE.relative_to(REPO)}")
            return 1
        for name, rs in tables(fixture).items():
            print(f"<!-- table: GS-PAT-1 {name} -->")
            print("\n".join(rs))
        return 0
    checks = [("examples", *example_diffs(text)), ("figures", *figure_diffs(text))]
    if fixture is None:
        checks.append(("fixture", 1, [f"MISSING fixture {FIXTURE.relative_to(REPO)}"]))
        checks.append(("tables", len(TABLES), [f"MISSING table GS-PAT-1 {t}" for t in TABLES]))
    else:
        checks.append(("hand-count", *count_diffs(fixture)))
        checks.append(("tables", *table_diffs(text, tables(fixture))))
    total = 0
    for name, seen, diffs in checks:
        for d in diffs:
            print(f"DIFF {d}")
        print(f"pattern-{name}: {seen} compared, {len(diffs)} difference(s)")
        total += len(diffs)
    print(f"pattern-check: {total} difference(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
