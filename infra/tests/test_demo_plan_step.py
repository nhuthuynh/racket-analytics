"""ST-064 unit tests: the pure plan step behind `make demo` (scripts/demo/demoplan.py).

No I/O. Negative cases first. The demo preferences are the PO's fixed demo player (sprint-04
ST-064: solo, 30 min, 3 sessions a week, no ball machine, intermediate), a body the plan API's
closed schema accepts (api-sprint-04 §2.1).
"""

from __future__ import annotations

import importlib.util
import sys

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit

_spec = importlib.util.spec_from_file_location("demoplan", SCRIPTS_DIR / "demo" / "demoplan.py")
assert _spec is not None
assert _spec.loader is not None
p = importlib.util.module_from_spec(_spec)
sys.modules["demoplan"] = p
_spec.loader.exec_module(p)


# ---------------------------------------------------------------- which plan to keep
@pytest.mark.parametrize(
    ("status", "body", "why"),
    [
        (404, {"error": {"code": "not_found"}}, "no plan API"),
        (404, None, "no plan API"),
        (401, {"error": {"code": "unauthenticated"}}, "HTTP 401"),
        (500, {"error": {"code": "internal"}}, "HTTP 500"),
        (200, {"sessions": []}, "no plan id"),
        (200, {"id": ""}, "no plan id"),
        (200, None, "no plan id"),
    ],
)
def test_plan_to_keep_refuses_an_answer_that_is_neither_a_plan_nor_no_plan(
    status: int, body: object, why: str
) -> None:
    with pytest.raises(ValueError, match=why):
        p.plan_to_keep(status, body)


def test_plan_to_keep_is_none_when_ivy_has_no_plan() -> None:
    assert p.plan_to_keep(404, {"error": {"code": "no_plan", "message": "x"}}) is None


def test_plan_to_keep_is_the_current_plan_id() -> None:
    assert p.plan_to_keep(200, {"id": "3f1c", "sessions": [{}]}) == "3f1c"


# ---------------------------------------------------------------- the demo preferences
def test_demo_preferences_are_the_fixed_demo_player() -> None:
    prefs = p.DEMO_PREFERENCES
    assert prefs["players_available"] == 1  # solo
    assert prefs["minutes_per_session"] == 30
    assert prefs["sessions_per_week"] == 3
    assert "ball_machine" not in prefs["equipment"]
    assert prefs["level"] == "intermediate"


def test_demo_preferences_are_a_closed_plan_api_body() -> None:
    fields = {"minutes_per_session", "sessions_per_week", "weekly_minutes", "players_available",
              "equipment", "level"}  # fmt: skip
    needs = {"wall", "half_court", "full_court", "ball_machine", "partner_feeder"}
    prefs = p.DEMO_PREFERENCES
    assert set(prefs) <= fields
    assert set(prefs["equipment"]) <= needs
    assert len(set(prefs["equipment"])) == len(prefs["equipment"])


def test_demo_preferences_cannot_be_changed_by_a_caller() -> None:
    with pytest.raises(TypeError):
        p.DEMO_PREFERENCES["level"] = "advanced"  # type: ignore[index]


# ---------------------------------------------------------------- the plan page
@pytest.mark.parametrize(
    ("origin", "url"),
    [
        ("https://localhost:3000", "https://localhost:3000/plan"),
        ("https://localhost:3000/", "https://localhost:3000/plan"),
        ("http://127.0.0.1:8080", "http://127.0.0.1:8080/plan"),
    ],
)
def test_plan_url_is_the_web_plan_page(origin: str, url: str) -> None:
    assert p.plan_url(origin) == url
