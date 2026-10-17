"""Independent reference for the Sprint 4 plan goal (docs/sprints/04/goal-scorecard.md G04-01..03).

Standard library only. The weakness ranking follows docs/domain/weakness-catalogue.md v0.1
(COACH-4: cells §2, tie-break §4, primary metric §5) over statslib's replay (side-out stepper,
PROVISIONAL-UNVERIFIED); `grade` checks QD-PL-01..04 as docs/architecture/coaching-plan.md §5
states them, on a plan body of api-sprint-04 §2.3. It neither imports nor mirrors
`racket.coaching`; infra/tests/test_planlib.py pins it to the catalogue's worked examples, so a
catalogue change changes this file and its tests with a TCR row (QA-HARNESS-4a).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import statslib as s

ORDER = ("unforced_errors", "serve_faults", "other_faults", "errors_under_pressure")
ORDER += ("opponent_winners",)  # catalogue order = tie-break order (§4)
NAMES = ("Unforced errors", "Serve faults", "Other faults", "Errors under pressure")
NAMES = dict(zip(ORDER, (*NAMES, "Opponent winners against you"), strict=True))
CELL = {"unforced_error": "unforced_errors", "forced_error": "errors_under_pressure"}
CELL |= {"winner": "opponent_winners"}
LABEL = {"AN-07:fault": "AN-07 fault", "AN-07:forced-error": "AN-07 FE"}  # §7 row labels
SHARE = {"serve_faults": "fault", "other_faults": "fault", "errors_under_pressure": "forced_error"}
LEVELS = ("beginner", "intermediate", "advanced")
REVIEWED = ("coach-reviewed", "verified")
UNIT = "rallies_lost_per_game"


def weakness(ending: str, kind: str | None) -> str | None:
    """§2: the weakness of a rally S lost; None = unattributed (FR-109)."""
    if ending == "fault":
        return "serve_faults" if kind == "serve" else "other_faults"
    return CELL.get(ending)


def target(w: str, serve: int, receive: int) -> str:
    """§5: the plan target of a weakness; AN-07 is split by share."""
    if w in ("serve_faults", "opponent_winners"):
        on_serve = serve >= receive
        if w == "serve_faults":
            return "AN-05" if on_serve else "AN-07:fault"
        return "AN-01" if on_serve else "AN-02"
    return {"unforced_errors": "AN-04", "other_faults": "AN-07:fault"}.get(w, "AN-07:forced-error")


def rank_facts(facts: list[tuple[str, str | None, bool]], games: int, rallies: int = 0) -> dict:
    """facts: (ending, fault kind, lost on serve) per rally S lost -> the §4 ranking."""
    tally = {w: [0, 0] for w in ORDER}
    for ending, kind, on_serve in facts:
        w = weakness(ending, kind)
        if w:
            tally[w][0 if on_serve else 1] += 1
    ranked = sorted(
        (w for w in ORDER if sum(tally[w])), key=lambda w: (-sum(tally[w]), ORDER.index(w))
    )
    out = []
    for w in ranked if games else []:
        sv, rc = tally[w]
        tgt = target(w, sv, rc)
        out.append({"id": w, "metric_id": tgt.split(":")[0], "target": tgt, "lost": sv + rc} | {
            "on_serve": sv, "on_receive": rc, "per_game": round((sv + rc) / games, 2),
            "on_serve_per_game": round(sv / games, 2), "on_receive_per_game": round(rc / games, 2),
        })  # fmt: skip
    return {"unit": UNIT, "side_out_verified": False, "games": games, "rallies": rallies} | {
        "weaknesses": out
    }


def script_games(script: dict) -> list[dict]:
    """The games of a GS-AN-1 tag script with its corrections applied."""
    games = copy.deepcopy(script["games"])
    flat = [tag for g in games for tag in g["tags"]]
    for c in script.get("corrections", []):
        flat[c["rally"] - 1][c["field"]] = c["value"]
    return games


def ranking(games: list[dict], side: str) -> dict:
    counted = [r for recs in s._records(games) for r in recs if not r["excluded"]]
    lost = [r for r in counted if r["winning_side"] not in (None, side)]
    facts = [(r["ending"], r["fault_kind"], r["serving_side"] == side) for r in lost]
    return rank_facts(facts, len(games), len(counted))


def render(rk: dict) -> str:
    """One §7 cell: `1. Unforced errors 10 = 10 + 0 (10.0/game; AN-04)<br>...`."""
    return "<br>".join(
        f"{i}. {NAMES[w['id']]} {w['lost']} = {w['on_serve']} + {w['on_receive']} "
        f"({w['lost'] / rk['games']:.1f}/game; {LABEL.get(w['target'], w['target'])})"
        for i, w in enumerate(rk["weaknesses"], start=1)
    )


def worked_examples(repo: Path) -> list[tuple[str, str, str]]:
    """(example, side, rendered ranking) for each catalogue §7 row, computed here."""
    fr120 = [("unforced_error", None, True)] * 10 + [("fault", "serve", False)] * 4
    rows = [("FR-120", "Ivy", render(rank_facts(fr120, 1)))]
    scripts = [("dict §2", {"games": [{"first_serving_side": "A", "tags": s.STATS_TAGS}]})]
    gold = Path(repo) / "backend" / "tests" / "regression" / "golden_matches"
    for f in sorted(gold.glob("gm*.script.json")):
        scripts.append((f.name.split("-")[0], json.loads(f.read_text(encoding="utf-8"))))
    for name, script in scripts:
        rows += [(name, side, render(ranking(script_games(script), side))) for side in "AB"]
    return rows


def catalogue_rows(text: str) -> dict[tuple[str, str], str]:
    rows = {}
    for line in text.splitlines():
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cols) == 5 and cols[2].isdigit():
            rows[(cols[0], cols[1])] = cols[3]
    return rows


def reference_check(repo: Path) -> dict[str, Any]:
    """G04-03 (a), reference side: planlib equals every worked example of the catalogue."""
    text = (Path(repo) / "docs" / "domain" / "weakness-catalogue.md").read_text(encoding="utf-8")
    want, got = catalogue_rows(text), worked_examples(repo)
    bad = [
        f"{e} {side}: {r!r} != {want.get((e, side))!r}"
        for e, side, r in got
        if want.get((e, side)) != r
    ]
    if len(want) != len(got):
        bad.append(f"{len(got)} rows computed, the catalogue has {len(want)}")
    return {"comparisons": len(got), "mismatches": bad, "ok": bool(got) and not bad}


def ranking_problems(want: dict, got: Any) -> list[str]:
    """G04-01 step 4: order, per-game numbers, metric, unit and the side-out-unverified mark."""
    if not isinstance(got, dict):
        return ["ranking missing"]
    keys = ("unit", "side_out_verified", "games", "rallies")
    p = [
        f"ranking {k}: expected {want[k]!r}, got {got.get(k)!r}"
        for k in keys
        if got.get(k) != want[k]
    ]
    ws = got.get("weaknesses") or []
    if [w.get("id") for w in ws] != [w["id"] for w in want["weaknesses"]]:
        return [*p, f"ranking order: got {[w.get('id') for w in ws]}"]
    for w, g in zip(want["weaknesses"], ws, strict=True):
        for k in ("metric_id", "per_game", "on_serve_per_game", "on_receive_per_game"):
            if not s._same(w[k], g.get(k)):
                p.append(f"ranking {w['id']} {k}: expected {w[k]!r}, got {g.get(k)!r}")
    return p


def load_library(root: Path) -> dict[str, dict]:
    """Every drill version under content/drills, keyed `id@version`."""
    library = {}
    for f in sorted(Path(root).glob("*/v*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        library[f"{d['id']}@{d['version']}"] = d
    return library


def _ref(a: dict) -> str:
    d = a.get("drill") or {}
    return f"{d.get('id')}@{d.get('version')}"


def _assignment(where: str, first: bool, a: dict, d: dict, pref: dict, budget: int) -> list[str]:
    """The rules one drill assignment must keep (coaching-plan §5)."""
    p, m, c = [], a.get("minutes") or 0, a.get("citation") or {}
    if not d["duration_min"] <= m <= d["duration_max"]:
        p.append(f"QD-PL-01: {where}: {m} min outside {d['duration_min']}-{d['duration_max']}")
    level = LEVELS.index(pref["level"])
    fits = d["players"] <= pref["players_available"] and set(d["needs"]) <= set(pref["equipment"])
    fits = fits and LEVELS.index(d["level_min"]) <= level <= LEVELS.index(d["level_max"])
    if not fits or d.get("review_status") not in REVIEWED or "deprecated_by" in d:
        p.append(f"QD-PL-02: {where}: players, needs, level or review status do not fit")
    if first and not ("warm-up" in d["skills"] and 5 <= m <= 10):
        p.append(f"QD-PL-03: {where}: warm-up of 5-10 min must come first")
    if m > budget * 2 // 5:
        p.append(f"QD-PL-03: {where}: {m} min over 40% of {budget}")
    if not c.get("n") or c.get("value") is None or c.get("metric_id") not in d["target_metrics"]:
        p.append(f"QD-PL-04: {where}: citation {c.get('metric_id')} n={c.get('n')} not citable")
    elif len(c.get("rally_ids") or []) > s.EVIDENCE_MAX:
        p.append(f"QD-PL-04: {where}: more than {s.EVIDENCE_MAX} rallies cited")
    return p


def grade(plan: dict, library: dict[str, dict]) -> list[str]:
    """QD-PL-01..03 and the plan-side part of QD-PL-04; [] only when every rule holds."""
    try:
        pref = plan["preferences"]
        spw, weekly = pref["sessions_per_week"], pref["weekly_minutes"]
        budget = min(pref["minutes_per_session"], weekly // spw)
        _ = LEVELS.index(pref["level"]), set(pref["equipment"]), pref["players_available"]
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return ["plan: preferences missing or malformed"]
    sessions, p, weeks = plan.get("sessions") or [], [], {}
    if len(sessions) != 2 * spw or {x.get("week") for x in sessions} != {1, 2}:
        p.append(f"plan: {len(sessions)} sessions, expected {2 * spw} over weeks 1-2")
    for sess in sessions:
        name = f"week {sess.get('week')} session {sess.get('index')}"
        items = sess.get("assignments") or []
        total = sum(a.get("minutes") or 0 for a in items)
        weeks[sess.get("week")] = weeks.get(sess.get("week"), 0) + total
        if sess.get("minutes_budget") != budget or total > budget:
            got = sess.get("minutes_budget")
            p.append(f"QD-PL-01: {name}: {total} min, budget {got} (expected {budget})")
        if not items or len({_ref(a) for a in items}) != len(items):
            p.append(f"plan: {name}: no assignment or a drill twice")
        for pos, a in enumerate(items, start=1):
            where, d = f"{name} #{pos} {_ref(a)}", library.get(_ref(a))
            if d is None:
                p.append(f"QD-PL-02: {where}: not in the drill library")
            else:
                p += _assignment(where, pos == 1, a, d, pref, budget)
    p += [f"QD-PL-01: week {w}: {t} min, weekly {weekly}" for w, t in weeks.items() if t > weekly]
    return p


def stats_value(metrics: dict, metric_id: str, side: str, share: str | None) -> tuple[Any, Any]:
    """(value, n) of a metric as GET stats shows it (coaching-plan §4: AN-04 n = games)."""
    m = metrics[metric_id][side]
    if metric_id == "AN-04":
        return m.get("value"), m.get("games")
    if metric_id == "AN-07":
        n = m.get("n") or 0
        return (round(m["counts"][share] / n, 4) if n else None), n
    return m.get("value"), m.get("n")


def citation_problems(
    plan: dict, stats: dict, side: str, evidence: dict, library: dict
) -> list[str]:
    """G04-01 step 6 (QD-PL-04): (metric, value, n) = GET stats; cited rallies in GET evidence."""
    metrics, p = (stats or {}).get("metrics") or {}, []
    for a in (a for x in plan.get("sessions") or [] for a in x.get("assignments") or []):
        c, aid = a.get("citation") or {}, a.get("id")
        mid, value, n = c.get("metric_id"), c.get("value"), c.get("n")
        if mid not in metrics or c.get("side") != side:
            p.append(f"QD-PL-04: {aid} {mid} side {c.get('side')} is not in GET stats for {side}")
            continue
        skills = library.get(_ref(a), {}).get("skills", [])
        shares = [SHARE[a["weakness_id"]]] if a.get("weakness_id") in SHARE else [
            x for x in ("fault", "forced_error") if f"share:{x.replace('_', '-')}" in skills
        ] or ["fault", "forced_error"]  # fmt: skip
        seen = [stats_value(metrics, mid, side, x) for x in shares]
        if not any(s._same(v, value) and k == n for v, k in seen):
            p.append(f"QD-PL-04: {aid} {mid} {value} n={n} is not GET stats ({seen})")
        for rid in c.get("rally_ids") or []:
            if rid not in evidence.get(mid, set()):
                p.append(f"QD-PL-04: {aid} {mid} rally {rid} is not in GET evidence")
    return p
