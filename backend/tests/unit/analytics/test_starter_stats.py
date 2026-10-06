"""Starter stats AN-01..AN-07 over the projected score sheet (ST-044; FR-100, FR-101; NFR-004;
metric-dictionary v0.1 rules 0.1-0.6).

sprint-03 §5 TDD order: 1. an empty sheet -> every metric n = 0, no value, flagged (AN-06 is
descriptive and never flagged, dictionary §1 AN-06); 2. replays and needs-decision rallies
excluded; 3. the metric-dictionary §2 worked example exactly (the coach's hand count);
4. per-player AN-04 never spreads untagged rallies; 5. AN-05 is flagged as a lower bound when a
serving-side fault has no subtype. The preset is PROVISIONAL-UNVERIFIED, so every metric that
reads the score sequence is ``@needs-verification`` (ADR 0009, ADR 0023).
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from racket.analytics.starter_stats import METRICS, counted_rallies, starter_stats
from racket.analytics.uncertainty import LowSamplePolicy
from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game, sheet, side_a_wins_game, tag

pytestmark = [pytest.mark.unit, pytest.mark.needs_verification]

SIDES = ("A", "B")


def stats_of(tags: list[dict[str, Any]]) -> dict[str, Any]:
    return starter_stats(one_game(tags))


# ---------------------------------------------------------------- 1. empty
def test_an_empty_sheet_has_no_values_and_every_proportion_is_flagged() -> None:
    empty = sheet([])
    stats = starter_stats(empty)
    assert set(stats) == set(METRICS)
    for side in SIDES:
        for metric in ("AN-01", "AN-02", "AN-05"):
            got = stats[metric][side]
            assert (got["k"], got["n"], got["value"], got["ci_low"], got["ci_high"]) == (
                0,
                0,
                None,
                None,
                None,
            )
            assert got["low_sample"] is True
        assert stats["AN-03"][side] == {
            "points": 0,
            "turns": 0,
            "value": None,
            "low_sample": True,
            "rallies": [],
        }
        assert stats["AN-04"][side]["value"] is None
        assert stats["AN-04"][side]["games"] == 0
        assert stats["AN-04"][side]["low_sample"] is True
        assert stats["AN-06"][side]["n"] == 0
        assert stats["AN-06"][side]["low_sample"] is False  # descriptive, never flagged
        assert stats["AN-07"][side]["n"] == 0
        assert stats["AN-07"][side]["low_sample"] is True


def test_a_started_game_with_no_rally_counts_as_a_game_in_scope() -> None:
    stats = starter_stats(sheet([{"first_serving_side": "A", "tags": []}]))
    assert stats["AN-04"]["A"]["games"] == 1
    assert stats["AN-04"]["A"]["value"] == 0.0


# ---------------------------------------------------------------- 2. exclusions (rule 0.1)
def test_a_replay_is_in_no_numerator_or_denominator() -> None:
    with_replay = stats_of([tag("A", "winner"), tag(None, "replay"), tag("B", "winner")])
    without = stats_of([tag("A", "winner"), tag("B", "winner")])
    for metric in METRICS:
        for side in SIDES:
            assert with_replay[metric][side] | {"rallies": None} == without[metric][side] | {
                "rallies": None
            }, metric
    # the rally references are the sheet's numbers, so the replay's number 2 is skipped
    assert with_replay["AN-01"]["A"]["rallies"] == [1, 3]


def test_rallies_after_the_game_end_need_a_decision_and_are_not_counted() -> None:
    tags = [*side_a_wins_game(), tag("B", "winner", None, "B1"), tag("B", "fault", "serve")]
    played = one_game(tags)
    assert [r["marker"] for r in played["rows"][-2:]] == ["needs_decision"] * 2
    stats = starter_stats(played)
    assert stats["AN-01"]["A"]["n"] == 11
    assert stats["AN-02"]["B"]["n"] == 11
    assert stats["AN-01"]["B"]["n"] == 0
    assert stats["AN-07"]["B"]["n"] == 0
    assert [r.number for r in counted_rallies(played)] == list(range(1, 12))


# ---------------------------------------------------------------- 3. the worked example (§2)
@pytest.fixture(scope="module")
def worked() -> dict[str, Any]:
    return stats_of(WORKED_EXAMPLE)


def _p(got: dict[str, Any]) -> tuple[int, int, float | None]:
    return got["k"], got["n"], got["value"]


def test_an_01_rallies_won_on_serve(worked: dict[str, Any]) -> None:
    assert _p(worked["AN-01"]["A"]) == (4, 7, pytest.approx(4 / 7, abs=1e-4))
    assert _p(worked["AN-01"]["B"]) == (4, 6, pytest.approx(4 / 6, abs=1e-4))
    assert worked["AN-01"]["A"]["rallies"] == [1, 2, 7, 9, 10, 11, 12]
    assert worked["AN-01"]["B"]["rallies"] == [3, 4, 5, 6, 13, 14]


def test_an_02_rallies_won_when_receiving(worked: dict[str, Any]) -> None:
    assert _p(worked["AN-02"]["A"]) == (2, 6, pytest.approx(2 / 6, abs=1e-4))
    assert _p(worked["AN-02"]["B"]) == (3, 7, pytest.approx(3 / 7, abs=1e-4))


def test_an_03_points_per_service_turn(worked: dict[str, Any]) -> None:
    for side in SIDES:
        got = worked["AN-03"][side]
        assert (got["points"], got["turns"], got["value"]) == (4, 2, 2.0)
        assert got["low_sample"] is True
    assert worked["AN-03"]["A"]["rallies"] == [1, 7, 9, 11]


def test_an_04_unforced_errors_per_game(worked: dict[str, Any]) -> None:
    a, b = worked["AN-04"]["A"], worked["AN-04"]["B"]
    assert (a["count"], a["games"], a["value"], a["by_player"], a["player_not_tagged"]) == (
        2,
        1,
        2.0,
        {"A1": 1, "A2": 1},
        0,
    )
    assert (b["count"], b["value"], b["by_player"], b["player_not_tagged"]) == (1, 1.0, {}, 1)
    assert a["low_sample"] is b["low_sample"] is True
    assert (a["rallies"], b["rallies"]) == ([4, 10], [9])


def test_an_05_serve_faults(worked: dict[str, Any]) -> None:
    a, b = worked["AN-05"]["A"], worked["AN-05"]["B"]
    assert (a["k"], a["n"], a["fault_type_not_tagged"], a["rallies"]) == (2, 7, 0, [2, 12])
    assert (b["k"], b["n"], b["value"], b["fault_type_not_tagged"]) == (0, 6, 0.0, 0)
    assert b["ci_low"] == 0.0


def test_an_06_longest_run(worked: dict[str, Any]) -> None:
    a, b = worked["AN-06"]["A"], worked["AN-06"]["B"]
    assert (a["longest"], a["n"]) == (3, 4)
    assert a["histogram"] == {"1": 1, "2": 0, "3": 1, "4": 0, "5+": 0}
    assert (b["longest"], b["n"]) == (2, 4)
    assert b["histogram"] == {"1": 0, "2": 2, "3": 0, "4": 0, "5+": 0}
    assert a["low_sample"] is b["low_sample"] is False


def test_an_07_how_rallies_ended(worked: dict[str, Any]) -> None:
    a, b = worked["AN-07"]["A"], worked["AN-07"]["B"]
    assert a["n"] == 6
    assert a["counts"] == {"winner": 2, "unforced_error": 2, "forced_error": 0, "fault": 2}
    assert b["n"] == 7
    assert b["counts"] == {"winner": 3, "unforced_error": 1, "forced_error": 1, "fault": 2}
    assert b["shares"]["winner"]["value"] == pytest.approx(3 / 7, abs=1e-4)
    assert a["shares"]["forced_error"]["ci_low"] == 0.0
    assert sum(s["k"] for s in b["shares"].values()) == b["n"]


def test_every_proportion_of_the_worked_example_is_low_sample(worked: dict[str, Any]) -> None:
    for metric in ("AN-01", "AN-02", "AN-05", "AN-07"):
        for side in SIDES:
            assert worked[metric][side]["low_sample"] is True, (metric, side)


def test_wilson_bounds_are_reported_for_proportions(worked: dict[str, Any]) -> None:
    got = worked["AN-01"]["A"]
    assert got["ci_low"] < got["value"] < got["ci_high"]
    assert (got["ci_low"], got["ci_high"]) == pytest.approx((0.2505, 0.8418), abs=1e-4)


# ---------------------------------------------------------------- 4. per player never spread
def test_untagged_unforced_errors_are_never_spread_across_players() -> None:
    stats = stats_of([tag("A", "unforced_error"), tag("A", "unforced_error", None, "B1")])
    b = stats["AN-04"]["B"]
    assert (b["count"], b["by_player"], b["player_not_tagged"]) == (2, {"B1": 1}, 1)


# ---------------------------------------------------------------- 5. AN-05 lower bound
def test_a_serving_side_fault_without_subtype_flags_serve_faults_as_a_lower_bound() -> None:
    many = [tag("A", "winner") for _ in range(10)]  # 10-0, A keeps serving
    stats = stats_of([*many, tag("B", "fault")])  # A (serving) faults, no subtype
    a = stats["AN-05"]["A"]
    assert (a["k"], a["fault_type_not_tagged"], a["low_sample"]) == (0, 1, True)


def test_a_receiving_side_fault_without_subtype_does_not_touch_serve_faults() -> None:
    stats = stats_of([tag("A", "fault")])  # B (receiving) faults
    assert stats["AN-05"]["B"]["fault_type_not_tagged"] == 0
    assert stats["AN-05"]["A"]["fault_type_not_tagged"] == 0


# ---------------------------------------------------------------- thresholds and games
def test_low_sample_thresholds_come_from_the_policy() -> None:
    lenient = LowSamplePolicy(
        min_proportion_n=1, max_interval_width=1.0, min_games=1, min_service_turns=1
    )
    stats = starter_stats(one_game(WORKED_EXAMPLE), lenient)
    assert stats["AN-01"]["A"]["low_sample"] is False
    assert stats["AN-03"]["A"]["low_sample"] is False
    assert stats["AN-04"]["A"]["low_sample"] is False


def test_two_games_count_and_runs_reset_at_game_end() -> None:
    played = sheet(
        [
            {"first_serving_side": "A", "tags": side_a_wins_game()},
            {"first_serving_side": "A", "tags": [tag("A", "winner"), tag("B", "unforced_error")]},
        ]
    )
    stats = starter_stats(played)
    a = stats["AN-06"]["A"]
    # game 2: A scores rally 12, then A's unforced error (B wins) is a side-out, no point
    assert (a["longest"], a["histogram"]["5+"], a["histogram"]["1"], a["n"]) == (11, 1, 1, 12)
    assert stats["AN-04"]["A"]["games"] == 2
    assert stats["AN-04"]["A"]["low_sample"] is False
    assert stats["AN-04"]["A"]["value"] == 0.5
    assert stats["AN-03"]["A"]["turns"] == 2
    assert stats["AN-01"]["A"]["rallies"][-2:] == [12, 13]


def test_a_game_after_an_unfinished_one_is_not_in_scope() -> None:
    played = sheet(
        [
            {"first_serving_side": "A", "tags": [tag("A", "winner")]},
            {"first_serving_side": "B", "tags": [tag("B", "winner")]},
        ]
    )
    stats = starter_stats(played)
    assert stats["AN-04"]["A"]["games"] == 1
    assert stats["AN-01"]["B"]["n"] == 0


# ---------------------------------------------------------------- properties
ENDINGS = st.sampled_from(["winner", "unforced_error", "forced_error", "fault", "replay"])


@st.composite
def tags(draw: st.DrawFn) -> dict[str, Any]:
    ending = draw(ENDINGS)
    if ending == "replay":
        return tag(None, ending)
    side = draw(st.sampled_from(SIDES))
    kind = draw(st.sampled_from([None, "serve", "nvz", "other"])) if ending == "fault" else None
    actor = side if ending == "winner" else ("B" if side == "A" else "A")
    player = draw(st.sampled_from([None, f"{actor}1", f"{actor}2"]))
    return tag(side, ending, kind, player)


@settings(max_examples=150, deadline=None)
@given(st.lists(tags(), max_size=40), st.sampled_from(SIDES))
def test_serve_and_receive_split_every_counted_rally(raw: list[dict[str, Any]], first: str) -> None:
    played = one_game(raw, first)
    stats = starter_stats(played)
    counted = len(counted_rallies(played))
    for side in SIDES:
        assert stats["AN-01"][side]["n"] + stats["AN-02"][side]["n"] == counted
        assert sum(stats["AN-07"][side]["counts"].values()) == stats["AN-07"][side]["n"]
        assert stats["AN-06"][side]["n"] == stats["AN-01"][side]["k"]  # side-out: only serving
    assert stats["AN-07"]["A"]["n"] + stats["AN-07"]["B"]["n"] == counted
    assert stats["AN-01"]["A"]["k"] + stats["AN-02"]["B"]["k"] == stats["AN-01"]["A"]["n"]


# ---------------------------------------------------------------- stored data never raises
def test_a_row_the_sheet_could_not_score_is_skipped_not_raised() -> None:
    played = one_game([tag("A", "winner"), tag("B", "winner")])
    played["rows"][0]["serving_side"] = None  # defensive: never produced by the projection
    played["rows"][1]["score_after"] = "not a call"
    stats = starter_stats(played)
    assert stats["AN-01"]["A"]["n"] == 1
    assert stats["AN-06"]["B"]["n"] == 0  # no readable score change, so no point
