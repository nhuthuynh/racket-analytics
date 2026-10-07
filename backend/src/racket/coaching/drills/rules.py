"""The drill rules of FR-140 over parsed drill files (ST-053; QD-DR-01, QD-DR-03). Pure.

Each document is checked against ``schema.json`` (QD-DR-01); then: every target metric (and every
``AN-*`` skill) is in the metric dictionary; every progression and regression names a drill of the
library, and neither graph has a cycle; no duration over 45 minutes and min <= max; level_min <=
level_max; the success criterion contains a number; a ``source``, or a ``coach_rationale``
labelled "(judgment)"; one file per (id, version); ``deprecated_by`` names a drill version.
Immutability over versions (the lock) is in ``lock.py``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from racket.coaching.drills.schema_check import drill_schema, errors

MAX_MINUTES = 45
LEVELS = ("beginner", "intermediate", "advanced")
_METRIC = re.compile(r"^AN-\d{2}$")
_NUMBER = re.compile(r"\d")


@dataclass(frozen=True, slots=True)
class Problem:
    source: str
    drill: str | None
    reason: str
    detail: str = ""

    def line(self) -> str:
        return f"FAIL {self.source}: drill {self.drill or '?'}: {self.reason}: {self.detail}"


def key(drill: Mapping[str, Any]) -> str:
    return f"{drill['id']}@{drill['version']}"


def _rules(src: str, d: Mapping[str, Any], metrics: frozenset[str], ids: set[str]) -> list[Problem]:
    found: list[Problem] = []

    def fail(reason: str, detail: str) -> None:
        found.append(Problem(src, d["id"], reason, detail))

    named = [*d["target_metrics"], *(s for s in d["skills"] if _METRIC.match(s))]
    if unknown := sorted({m for m in named if m not in metrics}):
        fail("unknown metric", ", ".join(unknown))
    for field in ("progressions", "regressions"):
        if missing := [x for x in d[field] if x not in ids]:
            fail(f"unknown {field[:-1]}", ", ".join(missing))
    if over := [f for f in ("duration_min", "duration_max") if d[f] > MAX_MINUTES]:
        fail("duration over 45", ", ".join(f"{f} = {d[f]} min" for f in over))
    elif d["duration_min"] > d["duration_max"]:
        fail("duration range", f"duration_min {d['duration_min']} > duration_max")
    if LEVELS.index(d["level_min"]) > LEVELS.index(d["level_max"]):
        fail("level range", f"{d['level_min']} > {d['level_max']}")
    if not _NUMBER.search(d["success_criterion"]):
        fail("criterion no number", repr(d["success_criterion"]))
    source = str(d.get("source", "")).strip()
    rationale = str(d.get("coach_rationale", "")).strip()
    if not source and not rationale:
        fail("no source", "neither source nor coach_rationale")
    elif rationale and not source and "(judgment)" not in rationale:
        fail("rationale not labelled", 'coach_rationale must say "(judgment)"')
    return found


def _cycles(graph: Mapping[str, Sequence[str]]) -> list[list[str]]:
    """Every elementary cycle once, rotated to start at its smallest id."""
    found: set[tuple[str, ...]] = set()

    def walk(node: str, trail: list[str]) -> None:
        for nxt in graph.get(node, ()):
            if nxt in trail:
                cycle = trail[trail.index(nxt) :]
                start = cycle.index(min(cycle))
                found.add(tuple(cycle[start:] + cycle[:start]))
            elif nxt in graph:
                walk(nxt, [*trail, nxt])

    for node in sorted(graph):
        walk(node, [node])
    return [list(c) for c in sorted(found)]


def lint_drills(docs: Mapping[str, object], metrics: frozenset[str]) -> list[Problem]:
    """Lint parsed drill documents (``source name -> JSON``) against the known metric ids."""
    problems: list[Problem] = []
    valid: dict[str, Mapping[str, Any]] = {}
    seen: dict[str, str] = {}
    for src in sorted(docs):
        doc = docs[src]
        drill_id = doc.get("id") if isinstance(doc, dict) else None
        if bad := list(errors(doc, drill_schema())):
            label = drill_id if isinstance(drill_id, str) else None
            problems.append(Problem(src, label, "schema", "; ".join(bad)))
            continue
        if not isinstance(doc, dict):  # pragma: no cover - the schema requires an object
            continue
        if key(doc) in seen:
            problems.append(Problem(src, doc["id"], "duplicate version", f"also {seen[key(doc)]}"))
            continue
        seen[key(doc)] = src
        valid[src] = doc
    ids = {d["id"] for d in valid.values()}
    latest: dict[str, Mapping[str, Any]] = {}
    for src, d in valid.items():
        problems += _rules(src, d, metrics, ids)
        if (dep := d.get("deprecated_by")) and dep not in seen:
            problems.append(Problem(src, d["id"], "unknown deprecated_by", dep))
        if d["id"] not in latest or d["version"] > latest[d["id"]]["version"]:
            latest[d["id"]] = d
    for field in ("progressions", "regressions"):
        graph = {i: [x for x in d[field] if x in latest] for i, d in latest.items()}
        for cycle in _cycles(graph):
            src = seen[key(latest[cycle[0]])]
            detail = " -> ".join([*cycle, cycle[0]])
            problems.append(Problem(src, cycle[0], f"{field[:-1]} cycle", detail))
    return problems
