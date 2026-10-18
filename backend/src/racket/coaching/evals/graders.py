"""Code graders for one eval run (ST-060; NFR-005 a; QD-QG-S7).

Each grader reads the run's plain-JSON output, the case and the library documents, never the
domain objects that built the plan, so a grader does not share a bug with the aggregate it
checks. Every finding starts with its grader id:

* ``OUTCOME``: a plan, or exactly the refusal the case expects;
* ``DRILL``: every drill id@version exists in the library, is coach-reviewed or verified and is
  not deprecated;
* ``CITE``: every assignment cites a metric the stats show, with the same version, value, k and
  n (pooled over the case's matches), rallies from that metric's evidence, and a "why" with n;
  a weakness drill cites its weakness's target, and the drill targets the cited metric;
* ``WEAKNESS``: the plan trains the ranking's top 3, in rank order;
* ``QD-PL-01``: 2 weeks x sessions per week; every session within its budget, every week within
  the weekly minutes, every drill within its own duration;
* ``QD-PL-02``: every drill fits the player's players, equipment and level;
* ``QD-PL-03``: every session starts with one warm-up of 5-10 minutes, no second warm-up, no
  drill over 40% of the session budget.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from racket.coaching.evals.cases import EvalCase

Docs = Mapping[str, Mapping[str, Any]]
REVIEWED = ("coach-reviewed", "verified")
LEVELS = ("beginner", "intermediate", "advanced")
WARM_UP = "warm-up"
WEEKS = 2
TOP = 3
SHARE_ENDINGS = {"AN-07:fault": "fault", "AN-07:forced-error": "forced_error"}


def grade(output: Mapping[str, Any], case: EvalCase, docs: Docs) -> list[str]:
    """Every finding of every grader; [] when the run passes."""
    plan = output.get("plan")
    refusal = output.get("refusal")
    if case.expect != "plan":
        if plan is not None or refusal != case.expect:
            got = "a plan" if plan is not None else f"the refusal {refusal}"
            return [f"OUTCOME: expected the refusal {case.expect}, got {got}"]
        return []
    if plan is None:
        return [f"OUTCOME: expected a plan, got the refusal {refusal}"]
    rows = list(_rows(plan))
    return (
        grade_drills(rows, docs)
        + grade_citations(plan, rows, output.get("stats", []), docs)
        + grade_weaknesses(plan, output.get("ranking", {}))
        + grade_constraints(plan, rows, case.preferences, docs)
    )


def _rows(plan: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    return [
        (f"week {s['week']} session {s['index']} drill {x['position']} {x['drill']}", x)
        for s in plan["sessions"]
        for x in s["assignments"]
    ]


def grade_drills(rows: Sequence[tuple[str, Mapping[str, Any]]], docs: Docs) -> list[str]:
    found = []
    for at, x in rows:
        doc = docs.get(x["drill"])
        if doc is None:
            found.append(f"DRILL: {at} is not in the library")
        elif doc["review_status"] not in REVIEWED:
            found.append(f"DRILL: {at} is {doc['review_status']}, not reviewed")
        elif "deprecated_by" in doc:
            found.append(f"DRILL: {at} is deprecated by {doc['deprecated_by']}")
    return found


def _pooled(stats: Sequence[Mapping[str, Any]], target: str) -> dict[str, Any] | None:
    """What the stats show for ``target`` over every match: version, k, n, evidence per match."""
    metric = target.split(":")[0]
    shown = [(s["match"], s["side"], s["metrics"][metric]) for s in stats if metric in s["metrics"]]
    if not shown:
        return None
    ending = SHARE_ENDINGS.get(target)
    k = sum(m["counts"].get(ending, 0) if ending else m["k"] for _, _, m in shown)
    return {
        "versions": {m["version"] for _, _, m in shown},
        "k": k,
        "n": sum(m["n"] for _, _, m in shown),
        "evidence": {(match, side): list(m["rally_ids"]) for match, side, m in shown},
    }


def _citation(at: str, c: Mapping[str, Any], why: str, shown: Mapping[str, Any]) -> list[str]:
    found = []
    target = c["target"]
    if shown["versions"] != {c["metric_version"]}:
        found.append(f"CITE: {at} {target} metric_version {c['metric_version']} is not "
                     f"{sorted(shown['versions'])}")  # fmt: skip
    for field in ("k", "n"):
        if c[field] != shown[field]:
            found.append(f"CITE: {at} {target} {field}={c[field]}, the stats show {shown[field]}")
    if shown["n"] and round(shown["k"] / shown["n"], 4) != c["value"]:
        found.append(f"CITE: {at} {target} value={c['value']}, the stats show "
                     f"{round(shown['k'] / shown['n'], 4)}")  # fmt: skip
    evidence = shown["evidence"]
    allowed = {(match, rally) for (match, _), ids in evidence.items() for rally in ids}
    for match, rally in c["rally_ids"]:
        if (match, rally) not in allowed:
            found.append(f"CITE: {at} {target} rally {rally} is not in its evidence")
    links = sorted([m, s, len(ids)] for (m, s), ids in evidence.items())
    if sorted(list(e) for e in c["evidence"]) != links:
        found.append(f"CITE: {at} {target} evidence links {c['evidence']} are not {links}")
    if str(c["n"]) not in why.replace("%", " ").split():
        found.append(f"CITE: {at} why {why!r} does not give n={c['n']}")
    return found


def grade_citations(
    plan: Mapping[str, Any],
    rows: Sequence[tuple[str, Mapping[str, Any]]],
    stats: Sequence[Mapping[str, Any]],
    docs: Docs,
) -> list[str]:
    targets = {w["id"]: w["target"] for w in plan["weaknesses"]}
    found = []
    for at, x in rows:
        c = x.get("citation")
        if not isinstance(c, Mapping):
            found.append(f"CITE: {at} has no citation")
            continue
        target = c["target"]
        wanted = targets.get(x["weakness_id"]) if x["weakness_id"] else None
        if wanted is not None and target != wanted:
            found.append(f"CITE: {at} cites {target}, its weakness trains {wanted}")
        doc = docs.get(x["drill"])
        if doc is not None and c["metric_id"] not in doc["target_metrics"]:
            found.append(f"CITE: {at} cites {c['metric_id']}, which the drill does not target")
        shown = _pooled(stats, target)
        if shown is None:
            found.append(f"CITE: {at} cites {target}, which the stats do not show")
            continue
        found += _citation(at, c, str(x.get("why", "")), shown)
    return found


def grade_weaknesses(plan: Mapping[str, Any], ranking: Mapping[str, Any]) -> list[str]:
    want = [(w["id"], w["target"], w["rank"]) for w in ranking.get("weaknesses", [])][:TOP]
    got = [(w["id"], w["target"], w["rank"]) for w in plan["weaknesses"]]
    if got != want:
        return [f"WEAKNESS: the plan trains {got}, the ranking's top {TOP} is {want}"]
    return []


def grade_constraints(
    plan: Mapping[str, Any],
    rows: Sequence[tuple[str, Mapping[str, Any]]],
    prefs: Mapping[str, Any],
    docs: Docs,
) -> list[str]:
    per_week = prefs["sessions_per_week"]
    weekly = prefs.get("weekly_minutes") or prefs["minutes_per_session"] * per_week
    budget = min(prefs["minutes_per_session"], weekly // per_week)
    cap = budget * 2 // 5
    found = []
    keys = [(s["week"], s["index"]) for s in plan["sessions"]]
    if keys != [(w, i) for w in range(1, WEEKS + 1) for i in range(1, per_week + 1)]:
        found.append(f"QD-PL-01: sessions {keys} are not {WEEKS} weeks x {per_week}")
    for week in range(1, WEEKS + 1):
        total = sum(x["minutes"] for s in plan["sessions"] if s["week"] == week
                    for x in s["assignments"])  # fmt: skip
        if total > weekly:
            found.append(f"QD-PL-01: week {week} totals {total} > {weekly} minutes")
    for s in plan["sessions"]:
        total = sum(x["minutes"] for x in s["assignments"])
        if total > budget:
            found.append(f"QD-PL-01: week {s['week']} session {s['index']} totals {total} > "
                         f"{budget} minutes")  # fmt: skip
        first = s["assignments"][0] if s["assignments"] else None
        if first is None or WARM_UP not in docs.get(first["drill"], {}).get("skills", ()):
            found.append(f"QD-PL-03: week {s['week']} session {s['index']} does not start "
                         "with a warm-up")  # fmt: skip
    for at, x in rows:
        doc = docs.get(x["drill"])
        if doc is not None:
            found += _assignment(at, x, doc, prefs, cap)
    return found


def _assignment(
    at: str, x: Mapping[str, Any], doc: Mapping[str, Any], prefs: Mapping[str, Any], cap: int
) -> list[str]:
    found = []
    minutes = x["minutes"]
    if not doc["duration_min"] <= minutes <= doc["duration_max"]:
        found.append(f"QD-PL-01: {at} {minutes} min outside {doc['duration_min']}.."
                     f"{doc['duration_max']}")  # fmt: skip
    level = LEVELS.index(prefs["level"])
    if doc["players"] > prefs["players_available"]:
        found.append(f"QD-PL-02: {at} needs {doc['players']} players")
    if missing := sorted(set(doc["needs"]) - set(prefs["equipment"])):
        found.append(f"QD-PL-02: {at} needs {missing}")
    if not LEVELS.index(doc["level_min"]) <= level <= LEVELS.index(doc["level_max"]):
        found.append(f"QD-PL-02: {at} is for {doc['level_min']}..{doc['level_max']}")
    if minutes > cap:
        found.append(f"QD-PL-03: {at} {minutes} min > 40% cap {cap}")
    warm = WARM_UP in doc["skills"]
    if x["position"] == 1 and warm and not 5 <= minutes <= 10:
        found.append(f"QD-PL-03: {at} warm-up of {minutes} min is not 5-10")
    if x["position"] > 1 and warm:
        found.append(f"QD-PL-03: {at} is a second warm-up")
    return found
