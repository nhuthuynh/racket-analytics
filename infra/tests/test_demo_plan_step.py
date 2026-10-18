"""ST-064 unit tests: the pure plan step behind `make demo` (scripts/demo/demoplan.py).

No I/O. Negative cases first. The demo body is the PO's fixed demo player in the plan API's
closed schema (api-sprint-04 §2.1).
"""

from __future__ import annotations

import pytest
from test_demo_plan import p  # demoplan, loaded from scripts/demo

pytestmark = pytest.mark.unit


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
def test_demo_preferences_are_the_fixed_demo_player_in_the_closed_plan_body() -> None:
    prefs = p.demo_preferences()
    assert set(prefs) <= {"minutes_per_session", "sessions_per_week", "weekly_minutes",
                          "players_available", "equipment", "level"}  # fmt: skip
    assert prefs["players_available"] == 1  # solo
    assert (prefs["minutes_per_session"], prefs["sessions_per_week"]) == (30, 3)
    assert prefs["equipment"] == ["wall"]  # no ball machine
    assert prefs["level"] == "intermediate"


# ---------------------------------------------------------------- the plan page
@pytest.mark.parametrize(
    ("origin", "url"),
    [
        ("https://localhost:3000", "https://localhost:3000/plan"),
        ("http://127.0.0.1:8080/", "http://127.0.0.1:8080/plan"),
    ],
)
def test_plan_url_is_the_web_plan_page(origin: str, url: str) -> None:
    assert p.plan_url(origin) == url
