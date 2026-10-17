"""COACH-4 worked examples of the weakness catalogue (pickleball-domain-coach).

Documentation tooling only, not product code. It applies docs/domain/weakness-catalogue.md
(cells §2, tie-break §4, primary metric §5) to the FR-120 scenario, the metric dictionary §2
example and the GS-AN-1 tag scripts, per side, and prints one table row per example and side.
It imports neither the product (`racket.coaching`) nor `scripts/measure/`; the rally replay is
the coach's own hand-count replay (hand_count_gs_an1.py, PROVISIONAL-UNVERIFIED preset).

Run:   python3 docs/domain/tools/weakness_example.py            # print the rows
       python3 docs/domain/tools/weakness_example.py --check    # rc 1 unless every row is in
                                                                 # weakness-catalogue.md verbatim
                                                                 # and every primary target
                                                                 # (AN-07 split by share) is a
                                                                 # coverage target of
                                                                 # drill-review-checklist.md §3
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hand_count_gs_an1 as hc  # sibling coach tool, not the product

CATALOGUE = hc.REPO / "docs" / "domain" / "weakness-catalogue.md"
CHECKLIST = hc.REPO / "docs" / "domain" / "drill-review-checklist.md"
# Primary-metric label (§5, §7) -> plan target a drill must match (checklist §3 targets).
# AN-07 is split by share (PE-R1-COACH4-01): the drill declares the share in `skills`.
TARGET = {
    "AN-01": "AN-01",
    "AN-02": "AN-02",
    "AN-04": "AN-04",
    "AN-05": "AN-05",
    "AN-07 fault": "AN-07:fault",
    "AN-07 FE": "AN-07:forced-error",
}
LEVELS = 3  # beginner, intermediate, advanced
# Catalogue order = tie-break order (§4).
ORDER = (
    "unforced_errors",
    "serve_faults",
    "other_faults",
    "errors_under_pressure",
    "opponent_winners",
)
NAMES = {
    "unforced_errors": "Unforced errors",
    "serve_faults": "Serve faults",
    "other_faults": "Other faults",
    "errors_under_pressure": "Errors under pressure",
    "opponent_winners": "Opponent winners against you",
}
# Section 2 of the catalogue: one row of S's lost rallies -> weakness.
ENDING = {
    "unforced_error": "unforced_errors",
    "forced_error": "errors_under_pressure",
    "winner": "opponent_winners",
}
# Section 2 example: metric-dictionary.md §2 (A serves first at 0-0-2; rally 8 is a replay).
DICT_EXAMPLE = [
    ("A", "winner", None),
    ("B", "fault", "serve"),
    ("B", "winner", None),
    ("B", "unforced_error", None),
    ("A", "forced_error", None),
    ("A", "fault", "nvz"),
    ("A", "winner", None),
    (None, "replay", None),
    ("A", "unforced_error", None),
    ("B", "unforced_error", None),
    ("A", "fault", None),
    ("B", "fault", "serve"),
    ("B", "winner", None),
    ("B", "winner", None),
]


def weakness(ending: str, kind: str | None) -> str | None:
    if ending == "fault":
        return "serve_faults" if kind == "serve" else "other_faults"
    return ENDING.get(ending)  # None -> unattributed (FR-109)


def primary(w: str, serve: int, receive: int) -> str:
    """Section 5: the metric a plan cites for the weakness."""
    if w == "serve_faults":
        return "AN-05" if serve >= receive else "AN-07 fault"
    if w == "opponent_winners":
        return "AN-01" if serve >= receive else "AN-02"
    return {
        "unforced_errors": "AN-04",
        "other_faults": "AN-07 fault",
        "errors_under_pressure": "AN-07 FE",
    }[w]


def lost_rows(script: dict) -> tuple[list[dict], int]:
    games = copy.deepcopy(script["games"])
    flat = [t for g in games for t in g["tags"]]
    for c in script.get("corrections", []):
        flat[c["rally"] - 1][c["field"]] = c["value"]
    rows, offset = [], 0
    for g in games:
        rows += hc.replay_game(g["tags"], g["first_serving_side"], offset, [])
        offset += len(g["tags"])
    return [r for r in rows if r["counted"]], len(games)


def rank(facts: list[tuple[str, str | None, bool]], games: int) -> tuple[str, str]:
    """facts: (ending, fault kind, lost on serve) for each rally S lost."""
    tally = {w: [0, 0] for w in ORDER}
    unattributed = [0, 0]
    for ending, kind, on_serve in facts:
        w = weakness(ending, kind)
        (tally[w] if w else unattributed)[0 if on_serve else 1] += 1
    ranked = sorted(
        (w for w in ORDER if sum(tally[w])), key=lambda w: (-sum(tally[w]), ORDER.index(w))
    )
    cells = [
        f"{i}. {NAMES[w]} {sum(tally[w])} = {tally[w][0]} + {tally[w][1]} "
        f"({sum(tally[w]) / games:.1f}/game; {primary(w, *tally[w])})"
        for i, w in enumerate(ranked, start=1)
    ]
    srv = sum(t[0] for t in tally.values()) + unattributed[0]
    rcv = sum(t[1] for t in tally.values()) + unattributed[1]
    return "<br>".join(cells), f"{srv + rcv} = {srv} + {rcv}; unattributed {sum(unattributed)}"


def rows() -> list[str]:
    out = []
    fr120 = [("unforced_error", None, True)] * 10 + [("fault", "serve", False)] * 4
    ranking, totals = rank(fr120, 1)
    out.append(f"| FR-120 | Ivy | 1 | {ranking} | {totals} |")
    tags = [{"winning_side": w, "ending": e, "fault_kind": k} for w, e, k in DICT_EXAMPLE]
    examples = [("dict §2", {"games": [{"first_serving_side": "A", "tags": tags}]})]
    examples += [
        (m.split("-")[0], json.loads((hc.SET_DIR / f"{m}.script.json").read_text()))
        for m in hc.MATCHES
    ]
    for name, script in examples:
        counted, games = lost_rows(script)
        for s in "AB":
            facts = [
                (r["ending"], r["kind"], r["server"] == s)
                for r in counted
                if r["win"] == hc.other(s)
            ]
            ranking, totals = rank(facts, games)
            out.append(f"| {name} | {s} | {games} | {ranking} | {totals} |")
    return out


def backticked(line: str) -> list[str]:
    return line.split("`")[1::2]


def target_problems() -> list[str]:
    """Every primary target of §5 must be a coverage target of checklist §3 (no share lost)."""
    text = CHECKLIST.read_text() if CHECKLIST.exists() else ""
    line = next((ln for ln in text.splitlines() if ln.startswith("- **Targets:**")), "")
    listed = backticked(line)
    out = [f"target {t} has no coverage cell" for t in TARGET.values() if t not in listed]
    out += [f"coverage target {t} is no primary target" for t in listed if t not in TARGET.values()]
    cells = f"**{LEVELS * len(TARGET)} cells**"
    if cells not in text:
        out.append(f"checklist §3 does not state {cells}")
    return out


def main() -> int:
    expected = rows()
    if "--check" not in sys.argv:
        print("\n".join(expected))
        return 0
    text = CATALOGUE.read_text() if CATALOGUE.exists() else ""
    missing = [r for r in expected if r not in text.splitlines()]
    for r in missing:
        print(f"MISSING in {CATALOGUE.relative_to(hc.REPO)}: {r}")
    print(f"weakness-examples: {len(expected) - len(missing)} of {len(expected)} rows match")
    ranking_cells = [c for r in expected for c in r.split("|")[4].strip().split("<br>")]
    labels = {c.rsplit("; ", 1)[1].rstrip(")") for c in ranking_cells}
    unknown = sorted(lb for lb in labels if lb not in TARGET)
    problems = [f"primary label {lb} has no plan target" for lb in unknown] + target_problems()
    for p in problems:
        print(f"TARGET {CHECKLIST.relative_to(hc.REPO)}: {p}")
    print(f"weakness-targets: {len(problems)} problem(s)")
    return 1 if missing or problems else 0


if __name__ == "__main__":
    sys.exit(main())
