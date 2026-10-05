"""Rally times and the outcome input (ST-026/ST-027; match-aggregate §2.1, §3 I5-I6).

sprint-02 §5 TDD order, negative first. ``Rally``: 1. end before start -> error; 2. overlapping
an earlier rally -> error; 3. times are integer ms from the video start (QD-TR-02).
``RallyOutcome`` input: 1. unknown ending -> error; 2. the responsible player for an error or
fault must be on the side that lost the rally; 3. for a winner, on the winning side;
4. the responsible player is optional. The side rules are judgment until the coach answers
match-aggregate §8 Q2 (ADR 0009 (a): no rule claim).
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.matches.scorebook.domain import (
    Ending,
    InvalidOutcome,
    InvalidRally,
    OutcomeInput,
    RallyTimes,
)
from racket.sports.pickleball.rules import FaultKind, RallyOutcome, Side

pytestmark = pytest.mark.unit


def outcome(**over: Any) -> OutcomeInput:
    body = {"ending": "winner", "winning_side": "A", "responsible_player": None,
            "fault_kind": None} | over  # fmt: skip
    return OutcomeInput.parse(body, format="doubles")


def codes(exc: pytest.ExceptionInfo[Any]) -> list[tuple[str | None, str]]:
    return [(f.field, f.code) for f in exc.value.fields]


# ---------------------------------------------------------------- Rally times
def test_end_before_start_is_refused() -> None:
    with pytest.raises(InvalidRally) as exc:
        RallyTimes.parse(5_000, 4_000)
    assert codes(exc) == [("end_ms", "end_before_start")]


def test_end_equal_to_start_is_refused() -> None:
    with pytest.raises(InvalidRally):
        RallyTimes.parse(4_000, 4_000)


def test_an_overlap_with_an_earlier_rally_is_refused() -> None:
    earlier = RallyTimes.parse(1_000, 5_000)
    with pytest.raises(InvalidRally) as exc:
        RallyTimes.parse(4_999, 9_000).check_after([earlier])
    assert codes(exc) == [("start_ms", "overlaps_rally")]


def test_a_rally_may_start_where_the_previous_one_ended() -> None:
    RallyTimes.parse(5_000, 9_000).check_after([RallyTimes.parse(1_000, 5_000)])


@pytest.mark.parametrize("raw", [1.5, "100", None, True, -1, 2**53])
def test_times_are_non_negative_integer_ms(raw: Any) -> None:
    with pytest.raises(InvalidRally):
        RallyTimes.parse(raw, 10_000)


@given(st.integers(0, 10**9), st.integers(1, 10**6))
def test_any_ordered_integer_pair_is_kept_exactly(start: int, length: int) -> None:
    times = RallyTimes.parse(start, start + length)
    assert (times.start_ms, times.end_ms) == (start, start + length)


# ---------------------------------------------------------------- outcome input
@pytest.mark.parametrize("ending", ["ace", "", "WINNER", None, 3])
def test_an_unknown_ending_is_refused(ending: Any) -> None:
    with pytest.raises(InvalidOutcome) as exc:
        outcome(ending=ending)
    assert exc.value.code == "invalid_outcome"
    assert codes(exc) == [("ending", "ending_invalid")]


@pytest.mark.parametrize("ending", ["unforced_error", "forced_error", "fault"])
def test_an_error_or_fault_by_the_winning_side_is_refused(ending: str) -> None:
    with pytest.raises(InvalidOutcome) as exc:
        outcome(ending=ending, winning_side="A", responsible_player="A2")
    assert codes(exc) == [("responsible_player", "must_be_on_losing_side")]


def test_a_winner_by_the_losing_side_is_refused() -> None:
    with pytest.raises(InvalidOutcome) as exc:
        outcome(ending="winner", winning_side="A", responsible_player="B1")
    assert codes(exc) == [("responsible_player", "must_be_on_winning_side")]


@pytest.mark.parametrize("ending", ["winner", "unforced_error", "forced_error", "fault"])
def test_the_responsible_player_is_optional(ending: str) -> None:
    assert outcome(ending=ending, winning_side="B").responsible_player is None


def test_a_replay_has_no_side_and_no_player() -> None:
    assert outcome(ending="replay", winning_side=None).to_engine() == RallyOutcome.replay()
    with pytest.raises(InvalidOutcome) as exc:
        outcome(ending="replay", winning_side="A")
    assert codes(exc) == [("winning_side", "replay_has_no_side")]
    with pytest.raises(InvalidOutcome):
        outcome(ending="replay", winning_side=None, responsible_player="A1")


def test_every_other_ending_needs_a_side() -> None:
    with pytest.raises(InvalidOutcome) as exc:
        outcome(ending="winner", winning_side=None)
    assert codes(exc) == [("winning_side", "side_required")]


@pytest.mark.parametrize("player", ["A3", "C1", "a1", "", 1])
def test_an_unknown_player_slot_is_refused(player: Any) -> None:
    with pytest.raises(InvalidOutcome) as exc:
        outcome(responsible_player=player)
    assert codes(exc) == [("responsible_player", "player_invalid")]


def test_a_singles_match_has_no_second_player() -> None:
    with pytest.raises(InvalidOutcome):
        OutcomeInput.parse({"ending": "winner", "winning_side": "A",
                            "responsible_player": "A2"}, format="singles")  # fmt: skip


def test_a_fault_kind_only_with_a_fault() -> None:
    assert outcome(ending="fault", fault_kind="nvz").fault_kind is FaultKind.NVZ
    with pytest.raises(InvalidOutcome) as exc:
        outcome(ending="winner", fault_kind="nvz")
    assert codes(exc) == [("fault_kind", "only_for_fault")]
    with pytest.raises(InvalidOutcome):
        outcome(ending="fault", fault_kind="lob")


def test_unknown_keys_are_refused() -> None:
    with pytest.raises(InvalidOutcome) as exc:
        OutcomeInput.parse({"ending": "winner", "winning_side": "A", "score": "11-0"},
                           format="doubles")  # fmt: skip
    assert codes(exc) == [(None, "unknown_field")]


@pytest.mark.parametrize(
    ("ending", "side", "expected"),
    [
        ("winner", "A", RallyOutcome.won_by(Side.A)),
        ("unforced_error", "B", RallyOutcome.won_by(Side.B)),
        ("forced_error", "A", RallyOutcome.won_by(Side.A)),
        ("fault", "A", RallyOutcome.fault(by=Side.B, kind=FaultKind.OTHER)),
    ],
)
def test_the_engine_outcome_carries_only_who_won(ending: str, side: str, expected: Any) -> None:
    got = outcome(ending=ending, winning_side=side).to_engine()
    assert got == expected
    assert got.rally_winner is Side(side)


def test_the_input_round_trips_through_its_json_form() -> None:
    value = outcome(ending="fault", winning_side="B", responsible_player="A2", fault_kind="foot")
    assert value.as_json() == {"ending": "fault", "winning_side": "B",
                               "responsible_player": "A2", "fault_kind": "foot"}  # fmt: skip
    assert OutcomeInput.parse(value.as_json(), format="doubles") == value
    assert Ending("fault") is value.ending
