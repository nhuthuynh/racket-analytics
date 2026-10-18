"""A small hand-built eval output for the ST-060 grader tests (NFR-005a): one reviewed warm-up,
one reviewed wall serve drill, a 2-week plan of one 30-minute session a week, and the stats it
cites. ``valid_output()`` passes every grader; each test breaks exactly one thing."""

from __future__ import annotations

import copy
from typing import Any

from tests.support.contract import Seam

GRADE = Seam(
    "racket.coaching.evals.graders:grade",
    "ST-060",
    "grade(output, case, library_docs) -> list[str], each finding prefixed by its grader id",
)
EVAL_CASE = Seam("racket.coaching.evals.cases:EvalCase", "ST-060")
EVALUATE = Seam(
    "racket.coaching.evals.runner:evaluate",
    "ST-060",
    "evaluate(cases, library, *, runs, planner=run_case) -> EvalReport",
)
EVAL_LIBRARY = Seam("racket.coaching.evals.library:EvalLibrary", "ST-060")


def doc(ref: str, **fields: Any) -> dict[str, Any]:
    drill_id, version = ref.split("@")
    base: dict[str, Any] = {
        "id": drill_id,
        "version": int(version),
        "skills": ["AN-05", "serve"],
        "target_metrics": ["AN-05"],
        "level_min": "beginner",
        "level_max": "advanced",
        "duration_min": 10,
        "duration_max": 15,
        "players": 1,
        "needs": ["wall"],
        "review_status": "coach-reviewed",
    }
    return base | fields


WARM = "t.warm-up@1"
SERVE = "t.serve@1"
DOCS = {
    WARM: doc(WARM, skills=["warm-up"], target_metrics=["AN-04"], duration_min=5,
              duration_max=10, needs=[]),
    SERVE: doc(SERVE),
}  # fmt: skip
PREFERENCES = {
    "minutes_per_session": 30,
    "sessions_per_week": 1,
    "players_available": 1,
    "equipment": ["wall"],
    "level": "intermediate",
}
SERVE_CITATION = {
    "metric_id": "AN-05",
    "target": "AN-05",
    "metric_version": "0.1",
    "value": 0.25,
    "n": 8,
    "k": 2,
    "low_sample": True,
    "rally_ids": [["m1", "r1"], ["m1", "r2"]],
    "evidence": [["m1", "A", 2]],
}
WARM_CITATION = {
    "metric_id": "AN-04",
    "target": "AN-04",
    "metric_version": "0.1",
    "value": 3.0,
    "n": 1,
    "k": 3,
    "low_sample": True,
    "rally_ids": [["m1", "r3"], ["m1", "r4"], ["m1", "r5"]],
    "evidence": [["m1", "A", 3]],
}


def _session(week: int) -> dict[str, Any]:
    return {
        "week": week,
        "index": 1,
        "minutes_budget": 30,
        "assignments": [
            {"position": 1, "drill": WARM, "minutes": 10, "weakness_id": None,
             "citation": copy.deepcopy(WARM_CITATION), "why": "Unforced errors: 3.0 over 1 game"},
            {"position": 2, "drill": SERVE, "minutes": 12, "weakness_id": "serve_faults",
             "citation": copy.deepcopy(SERVE_CITATION), "why": "Serve faults: 25% of 8 serves"},
        ],
    }  # fmt: skip


def valid_output() -> dict[str, Any]:
    return {
        "case": "unit-1",
        "refusal": None,
        "ranking": {
            "weaknesses": [
                {"id": "serve_faults", "target": "AN-05", "rank": 1},
                {"id": "unforced_errors", "target": "AN-04", "rank": 2},
            ]
        },
        "stats": [
            {
                "match": "m1",
                "side": "A",
                "rallies": 14,
                "metrics": {
                    "AN-04": {
                        "name": "Unforced errors",
                        "version": "0.1",
                        "k": 3,
                        "n": 1,
                        "counts": {},
                        "low_sample": True,
                        "rally_ids": ["r3", "r4", "r5"],
                    },
                    "AN-05": {
                        "name": "Serve faults",
                        "version": "0.1",
                        "k": 2,
                        "n": 8,
                        "counts": {},
                        "low_sample": True,
                        "rally_ids": ["r1", "r2"],
                    },
                    "AN-07": {
                        "name": "Rally endings",
                        "version": "0.1",
                        "k": 0,
                        "n": 9,
                        "counts": {"fault": 4, "forced_error": 1, "unforced_error": 3, "winner": 1},
                        "low_sample": True,
                        "rally_ids": ["r1", "r2", "r6"],
                    },
                },
            }
        ],
        "plan": {
            "library_version": "sha256:test",
            "preferences": dict(PREFERENCES, weekly_minutes=30),
            "weaknesses": [
                {"id": "serve_faults", "target": "AN-05", "rank": 1},
                {"id": "unforced_errors", "target": "AN-04", "rank": 2},
            ],
            "unfitted": [{"weakness_id": "unforced_errors", "reason": "no_drill_fits"}],
            "limited_data": {"rallies": 14},
            "sessions": [_session(1), _session(2)],
        },
    }


def case(expect: str = "plan", **preferences: Any) -> Any:
    return EVAL_CASE.load()(
        id="unit-1",
        description="unit test case",
        preferences=dict(PREFERENCES, **preferences),
        matches=(),
        expect=expect,
    )


def grade(output: dict[str, Any], expect: str = "plan", **preferences: Any) -> list[str]:
    findings: list[str] = GRADE.load()(output, case(expect, **preferences), DOCS)
    return findings


def first_drill(output: dict[str, Any], week: int = 1, position: int = 2) -> dict[str, Any]:
    row: dict[str, Any] = output["plan"]["sessions"][week - 1]["assignments"][position - 1]
    return row
