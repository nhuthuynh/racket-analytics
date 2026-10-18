"""FIX-04-1b unit tests: live_plan.py generates with a body the plan contract accepts (G04-02).

Root cause of G04-02 (a)/(c) never being measurable: live_plan.PREFS lacked the required
``equipment`` and ``level`` of api-sprint-04 §2.1, so every POST /me/plan would be 422 and the
generate sample stays empty. The oracle (plan_contract) reads the contract table itself.
"""

from __future__ import annotations

import plan_contract as pc
import plan_fixtures as pf
import pytest

pytestmark = pytest.mark.unit
live = pf.load("live_plan")
SOLO_WALL = {"minutes_per_session": 30, "sessions_per_week": 3, "players_available": 1}
SOLO_WALL |= {"equipment": ["wall"], "level": "intermediate"}


def test_the_oracle_refuses_a_body_without_level_and_equipment() -> None:
    body = {k: v for k, v in SOLO_WALL.items() if k not in ("level", "equipment")}
    assert pc.problems(body) == [("equipment", "required"), ("level", "required")]


@pytest.mark.parametrize(
    ("change", "want"),
    [
        ({"minutes_per_session": 14}, [("minutes_per_session", "out_of_range")]),
        ({"sessions_per_week": "3"}, [("sessions_per_week", "invalid")]),
        ({"players_available": 5}, [("players_available", "out_of_range")]),
        ({"equipment": ["wall", "wall"]}, [("equipment", "duplicate")]),
        ({"equipment": ["net"]}, [("equipment", "unknown_value")]),
        ({"level": "pro"}, [("level", "unknown_value")]),
        ({"colour": "red"}, [(None, "unknown_field")]),
    ],
)
def test_the_oracle_gives_the_contract_code_for_a_bad_field(change: dict, want: list) -> None:
    assert pc.problems(SOLO_WALL | change) == want


def test_the_oracle_reads_every_body_field_of_the_contract_table() -> None:
    table = pc.fields()
    assert list(table) == [
        "minutes_per_session",
        "sessions_per_week",
        "weekly_minutes",
        "players_available",
        "equipment",
        "level",
    ]
    assert [n for n, f in table.items() if not f.required] == ["weekly_minutes"]


def test_the_oracle_accepts_the_contracts_own_example_body() -> None:
    assert pc.problems(SOLO_WALL) == []


def test_the_harness_body_has_every_required_field_of_the_contract() -> None:
    assert pc.problems(live.PREFS) == []


def test_the_harness_body_is_the_scorecard_profile_one_player_at_a_wall() -> None:
    # G04-01/G04-02 profile: the coach's worked example fits a solo wall plan (plan_fixtures).
    assert {k: live.PREFS[k] for k in ("equipment", "level")} == {
        "equipment": pf.PREFS["equipment"],
        "level": pf.PREFS["level"],
    }
