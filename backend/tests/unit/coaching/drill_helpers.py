"""A valid drill and the known metric ids for the drill lint unit tests (ST-053)."""

from __future__ import annotations

from typing import Any

METRICS = frozenset({"AN-01", "AN-04", "AN-05"})


def a_drill(drill_id: str = "pb.test.drop-ladder", version: int = 1, **over: Any) -> dict[str, Any]:
    drill: dict[str, Any] = {
        "id": drill_id,
        "version": version,
        "name": "Drop ladder",
        "summary": "Third-shot drops into the kitchen from the baseline.",
        "skills": ["AN-04", "third_shot_drop"],
        "target_metrics": ["AN-04"],
        "level_min": "beginner",
        "level_max": "intermediate",
        "duration_min": 10,
        "duration_max": 15,
        "players": 2,
        "needs": ["half_court"],
        "equipment": ["balls"],
        "setup": ["Feeder at the kitchen line", "Hitter at the baseline"],
        "success_criterion": "8 of 10 drops bounce in the kitchen",
        "progressions": [],
        "regressions": [],
        "safety_notes": "",
        "coach_rationale": "Drop consistency before speed (judgment)",
        "review_status": "draft",
    }
    drill.update(over)
    return drill
