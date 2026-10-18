"""Plays eval cases through Coaching's rules-only workflow and grades them (ST-060; NFR-005 a).

``run_case`` is one run: each match's tag script becomes a score sheet through Match & Scoring's
port, its rally facts and published metrics come through Analytics' port, then the same steps
as ``POST /me/plan``: weakness ranking (ST-055 ACL), citations (ST-057 ACL), ``citable`` drills,
``assemble`` (ST-056) and ``CitedPlan``. Its output is plain JSON: the stats the player would
see, the ranking, the cited plan or the refusal.

``evaluate`` runs every case ``runs`` times; a case passes only when every run passes every
grader and all runs are byte-identical (pass^3 for ``runs=3``).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from racket.analytics import public as analytics
from racket.coaching.evals.cases import EvalCase
from racket.coaching.evals.graders import grade
from racket.coaching.evals.library import EvalLibrary
from racket.coaching.plan import acl as citation_acl
from racket.coaching.plan.domain import (
    CitedPlan,
    Infeasible,
    PlanWeakness,
    Preferences,
    assemble,
    citable,
)
from racket.coaching.weakness import acl as weakness_acl
from racket.matches import public as matches

Planner = Callable[[EvalCase, EvalLibrary], Mapping[str, Any]]
_CASES = uuid.UUID("5a1d0000-0000-4000-8000-000000000060")  # match ids: uuid5(case/index)


def preferences(raw: Mapping[str, Any]) -> Preferences:
    return Preferences(
        minutes_per_session=raw["minutes_per_session"],
        sessions_per_week=raw["sessions_per_week"],
        players_available=raw["players_available"],
        equipment=frozenset(raw["equipment"]),
        level=raw["level"],
        weekly_minutes=raw.get("weekly_minutes"),
    )


def _metrics(found: analytics.MatchMetrics) -> dict[str, Any]:
    return {
        m: {
            "name": f.name,
            "version": f.version,
            "k": f.k,
            "n": f.n,
            "counts": dict(sorted(f.counts.items())),
            "low_sample": f.low_sample,
            "rally_ids": list(f.rally_ids),
        }
        for m, f in sorted(found.metrics.items())
    }


def run_case(case: EvalCase, library: EvalLibrary) -> dict[str, Any]:
    """One run of one case, as plain JSON (no clock, no randomness)."""
    facts, metrics = [], []
    for index, m in enumerate(case.matches):
        match_id = uuid.uuid5(_CASES, f"{case.id}/{index}")
        sheet = matches.sheet_of_tags(m["games"], format=m["format"], best_of=m["best_of"])
        facts.append((match_id, m["side"], analytics.facts_of_sheet(sheet)))
        metrics.append(
            (str(match_id), m["side"], analytics.metric_facts_of_sheet(sheet, m["side"]))
        )
    metrics.sort(key=lambda x: x[0])  # citations_for reads matches in match id order
    ranking = weakness_acl.ranking_of(f for f in facts if f[2].rallies)
    cited = citation_acl.citations_from([x for x in metrics if x[2].rallies])
    out: dict[str, Any] = {
        "case": case.id,
        "library_version": library.version,
        "ranking": {
            "games": ranking.games,
            "rallies": ranking.rallies,
            "provisional": ranking.provisional,
            "weaknesses": [
                {
                    "id": w.id,
                    "target": w.plan_target,
                    "rank": w.rank,
                    "lost": w.lost,
                    "lost_on_serve": w.lost_on_serve,
                    "lost_on_receive": w.lost_on_receive,
                }
                for w in ranking.weaknesses
            ],
        },
        "stats": [
            {"match": m, "side": side, "rallies": f.rallies, "metrics": _metrics(f)}
            for m, side, f in metrics
        ],
        "plan": None,
        "refusal": None,
    }
    weaknesses = [PlanWeakness(w.id, w.plan_target, w.rank) for w in ranking.weaknesses]
    drills = citable(library.drills, cited.citations)
    plan = assemble(weaknesses, preferences(case.preferences), drills, library.version)
    if isinstance(plan, Infeasible):
        out["refusal"] = plan.reason
    else:
        out["plan"] = CitedPlan(plan, cited.citations, cited.rallies).content()
    return out


def canonical(output: Mapping[str, Any]) -> bytes:
    return json.dumps(output, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    runs: int
    failures: tuple[str, ...]
    digests: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures

    def line(self) -> str:
        if self.passed:
            return f"PASS {self.case_id} runs={self.runs} {self.digests[0]}"
        return f"FAIL {self.case_id} runs={self.runs}: " + "; ".join(self.failures)


@dataclass(frozen=True, slots=True)
class EvalReport:
    runs: int
    library: str
    results: tuple[CaseResult, ...]
    problems: tuple[str, ...] = ()  # set-level failures, e.g. too few cases

    @property
    def passed(self) -> int:
        return sum(r.passed for r in self.results)

    @property
    def exit_code(self) -> int:
        return 0 if self.passed == len(self.results) and not self.problems else 1

    def lines(self) -> list[str]:
        total = len(self.results)
        rate = f"{100 * self.passed // total}%" if total else "n/a"
        summary = f"pass^{self.runs}: {self.passed} of {total} cases passed all {self.runs} runs"
        problems = [f"FAIL eval set: {p}" for p in self.problems]
        return [r.line() for r in self.results] + problems + [f"{summary} ({rate})"]

    def as_json(self) -> dict[str, Any]:
        return {
            "runs": self.runs,
            "library": self.library,
            "passed": self.passed,
            "problems": list(self.problems),
            "cases": [
                {"id": r.case_id, "passed": r.passed, "failures": list(r.failures),
                 "digests": list(r.digests)}
                for r in self.results
            ],
        }  # fmt: skip


def evaluate_case(case: EvalCase, library: EvalLibrary, runs: int, planner: Planner) -> CaseResult:
    failures: list[str] = []
    blobs: list[bytes] = []
    for run in range(1, runs + 1):
        try:
            output = planner(case, library)
            blob = canonical(output)
        except Exception as exc:  # noqa: BLE001 - a crashing run is a failed run, named
            failures.append(f"run {run}: {type(exc).__name__}: {exc}")
            continue
        blobs.append(blob)
        failures += [f for f in grade(output, case, library.docs) if f not in failures]
    digests = tuple("sha256:" + hashlib.sha256(b).hexdigest() for b in blobs)
    if len(set(digests)) > 1:
        failures.append(f"pass^{runs}: the {runs} runs differ ({len(set(digests))} outputs)")
    return CaseResult(case.id, runs, tuple(failures), digests)


def evaluate(
    cases: Sequence[EvalCase],
    library: EvalLibrary,
    *,
    runs: int = 3,
    planner: Planner = run_case,
    min_cases: int = 0,
) -> EvalReport:
    if runs < 1:
        raise ValueError(f"runs must be at least 1, not {runs}")
    results = tuple(evaluate_case(c, library, runs, planner) for c in cases)
    problems = []
    if len(cases) < min_cases:
        problems.append(f"{len(cases)} case(s), at least {min_cases} required (NFR-005a)")
    return EvalReport(runs, library.root, results, tuple(problems))
