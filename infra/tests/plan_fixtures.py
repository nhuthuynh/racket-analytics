"""QA-HARNESS-4a test data: a drill library and a plan that keeps QD-PL-01..04 (G04-01 prefs).

Citations are the statslib reference of the worked example for Ivy's side A, so a stub can serve
the same numbers as GET stats. Standard library only; no product imports.
"""

from __future__ import annotations

import copy
import importlib.util
import sys

from conftest import SCRIPTS_DIR


def load(name: str):
    measure = str(SCRIPTS_DIR / "measure")
    if measure not in sys.path:
        sys.path.insert(0, measure)
    spec = importlib.util.spec_from_file_location(name, f"{measure}/{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


s = load("statslib")
PREFS = {"minutes_per_session": 30, "sessions_per_week": 3, "weekly_minutes": 90}
PREFS |= {"players_available": 1, "equipment": ["wall"], "level": "intermediate"}
REF = s.starter_stats([{"first_serving_side": "A", "tags": s.STATS_TAGS}])
FIT = {"level_min": "beginner", "level_max": "advanced", "needs": ["wall"], "players": 1}


def _drill(name: str, skills: list[str], dmin: int = 5, dmax: int = 12) -> dict:
    return FIT | {
        "id": f"pb.test.{name}",
        "version": 1,
        "skills": skills,
        "target_metrics": ["AN-02", "AN-04"],
        "duration_min": dmin,
        "duration_max": dmax,
        "review_status": "coach-reviewed",
    }


DRILLS = [_drill("warm", ["warm-up"], 5, 10), _drill("a", ["serve"]), _drill("b", ["dink"])]
ALT = _drill("c", ["drop"])  # the "Not for me" replacement


def library() -> dict[str, dict]:
    return {f"{d['id']}@1": d for d in [*DRILLS, ALT]}


def cite(metric: str) -> dict:
    m = REF[metric]["A"]
    n = m["games"] if metric == "AN-04" else m["n"]
    ids = [f"r{x}" for x in m["rallies"][:10]]
    return {"metric_id": metric, "side": "A", "value": m["value"], "n": n, "rally_ids": ids}


def _a(sid: str, pos: int, drill: dict, minutes: int, weakness: str | None, metric: str) -> dict:
    ref = {k: drill[k] for k in ("id", "version", "players", "needs", "skills")}
    body = {"id": f"{sid}a{pos}", "position": pos, "drill": ref, "minutes": minutes}
    return body | {"weakness_id": weakness, "warm_up": pos == 1, "citation": cite(metric)}


def _session(n: int) -> dict:
    sid = f"s{n}"
    items = [
        _a(sid, 1, DRILLS[0], 6, None, "AN-02"),
        _a(sid, 2, DRILLS[1], 12, "opponent_winners", "AN-02"),
        _a(sid, 3, DRILLS[2], 12, "unforced_errors", "AN-04"),
    ]
    return {"id": sid, "week": n // 3 + 1, "index": n % 3 + 1, "minutes_budget": 30} | {
        "done": False,
        "assignments": items,
    }


def plan(ranking: dict | None = None) -> dict:
    return {
        "id": "p1",
        "version": 1,
        "content_digest": "sha256:0",
        "preferences": copy.deepcopy(PREFS),
        "ranking": ranking,
        "limited_data": {"rallies": 13},
        "sessions": [_session(n) for n in range(6)],
    }
