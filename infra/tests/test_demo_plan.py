"""MVP-03 unit tests: the pure demo plan behind `make demo` (scripts/demo/demoplan.py).

No I/O. Negative cases first in each group. The rally plan is checked against the Quick Tag
rules the API enforces (api-sprint-02 §2; scorebook ``OutcomeInput``/``RallyTimes``): I5 times
inside the video and not overlapping, I6 the responsible player on the side that made the
ending, a fault kind only on a fault, a replay with no side; and against taglib's independent
side-out stepper, so game 1 is still running after the last demo rally.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit


def _load(directory: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, directory / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


p = _load(SCRIPTS_DIR / "demo", "demoplan")
t = _load(SCRIPTS_DIR / "measure", "taglib")

SIXTY_S = 60_000


# ---------------------------------------------------------------- profile (dev only)
@pytest.mark.parametrize(
    ("env", "reason"),
    [
        ({"APP_ENV": "prod"}, "only against the dev profile"),
        ({"APP_ENV": "production"}, "only against the dev profile"),
        ({"APP_ENV": "staging"}, "only against the dev profile"),
        ({"APP_ENV": "test"}, "only against the dev profile"),
        ({"APP_ENV": "dev", "DEV_IDENTITY_ENABLED": "false"}, "dev sign-in is disabled"),
    ],
)
def test_refusal_names_why_a_profile_is_refused(env: dict[str, str], reason: str) -> None:
    refusal = p.refusal(env)
    assert refusal is not None
    assert reason in refusal


@pytest.mark.parametrize(
    "env",
    [{"APP_ENV": "dev"}, {"APP_ENV": "dev", "DEV_IDENTITY_ENABLED": "true"}, {}],
)
def test_refusal_allows_the_dev_profile_and_an_unknown_one(env: dict[str, str]) -> None:
    # Unknown (no env file): the live GET /dev/users check decides (the API mounts /dev/* only
    # with the dev provider enabled).
    assert p.refusal(env) is None


def test_parse_env_file_reads_plain_assignments_and_skips_comments() -> None:
    text = "# comment\nAPP_ENV=dev\n\nDEV_IDENTITY_ENABLED = true\nNOT A LINE\nX='q'\n"
    assert p.parse_env_file(text) == {"APP_ENV": "dev", "DEV_IDENTITY_ENABLED": "true", "X": "q"}


# ---------------------------------------------------------------- rally plan
def test_rally_plan_refuses_a_video_too_short_for_the_plan() -> None:
    with pytest.raises(ValueError, match="too short"):
        p.rally_plan(p.RALLIES * 1_000 - 1)


def test_rally_plan_has_twelve_rallies_inside_the_video_in_order_without_overlap() -> None:
    plan = p.rally_plan(SIXTY_S)
    assert len(plan) == p.RALLIES == 12
    previous_end = 0
    for tag in plan:
        assert isinstance(tag["start_ms"], int)
        assert isinstance(tag["end_ms"], int)
        assert previous_end <= tag["start_ms"] < tag["end_ms"] <= SIXTY_S
        previous_end = tag["end_ms"]


def test_rally_plan_is_deterministic_and_scales_with_the_video() -> None:
    assert p.rally_plan(SIXTY_S) == p.rally_plan(SIXTY_S)
    assert p.rally_plan(90_000)[-1]["end_ms"] > p.rally_plan(SIXTY_S)[-1]["end_ms"]


def test_rally_plan_sends_only_quick_tag_fields() -> None:
    allowed = {"start_ms", "end_ms", "ending", "winning_side", "responsible_player", "fault_kind"}
    assert all(set(tag) <= allowed for tag in p.rally_plan(SIXTY_S))


def test_every_planned_outcome_is_a_valid_quick_tag() -> None:
    slots = {"A1", "A2", "B1", "B2"}
    for tag in p.rally_plan(SIXTY_S):
        ending, side = tag["ending"], tag["winning_side"]
        player, kind = tag.get("responsible_player"), tag.get("fault_kind")
        assert ending in t.ENDINGS
        if ending == "replay":
            assert side is None
            assert player is None
            assert kind is None
            continue
        assert side in ("A", "B")
        if player is not None:
            assert player in slots
            on_winning_side = player[0] == side
            assert on_winning_side if ending == "winner" else not on_winning_side  # I6
        assert kind is None or (ending == "fault" and kind in p.FAULT_KINDS)


def test_both_sides_have_winners_and_errors_so_every_side_has_stats() -> None:
    plan = p.rally_plan(SIXTY_S)
    for side in ("A", "B"):
        assert any(r["ending"] == "winner" and r["winning_side"] == side for r in plan)
        assert any(r["ending"] != "winner" and r["winning_side"] not in (side, None) for r in plan)
    assert any(r["ending"] == "replay" for r in plan)
    assert any(r.get("responsible_player") for r in plan)


def test_game_one_is_still_running_after_the_last_demo_rally() -> None:
    state = t.new_doubles_game(p.FIRST_SERVING_SIDE)
    for tag in p.rally_plan(SIXTY_S):
        state = t.step_doubles(state, tag["winning_side"] or "replay")
    assert state.winner is None


# ---------------------------------------------------------------- idempotence
def test_choose_creates_the_demo_match_when_there_is_none() -> None:
    assert p.choose([], planned=12) == p.Action("create", p.DEMO_TITLE, None)


def test_choose_reuses_a_complete_demo_match() -> None:
    found = [p.DemoMatch("m1", "Demo match", "video_received", 12)]
    assert p.choose(found, planned=12) == p.Action("reuse", "Demo match", "m1")


def test_choose_numbers_a_new_match_when_the_old_one_is_incomplete() -> None:
    found = [
        p.DemoMatch("m1", "Demo match", "uploading", 0),
        p.DemoMatch("m2", "Demo match (2)", "video_received", 3),
    ]
    assert p.choose(found, planned=12) == p.Action("create", "Demo match (3)", None)


def test_choose_with_new_always_creates_the_next_numbered_match() -> None:
    found = [p.DemoMatch("m1", "Demo match", "video_received", 12)]
    assert p.choose(found, planned=12, new=True) == p.Action("create", "Demo match (2)", None)


@pytest.mark.parametrize(
    ("title", "demo"),
    [
        ("Demo match", True),
        ("Demo match (7)", True),
        ("Demo match 2", False),
        ("My demo match", False),
        ("Demo match (x)", False),
    ],
)
def test_only_demo_titles_count_as_demo_matches(title: str, demo: bool) -> None:
    assert p.is_demo_title(title) is demo


def test_stats_url_points_at_the_matchs_stats_page() -> None:
    url = p.stats_url("https://localhost:3000/", "0b7c")
    assert url == "https://localhost:3000/matches/0b7c/stats"
