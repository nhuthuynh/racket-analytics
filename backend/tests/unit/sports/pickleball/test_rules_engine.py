"""apply, positions, faults and fold (ST-020; sprint-01 §5 rows in order; scoring-engine.md §3).

BE unit tests, negative cases first. Configurations are explicit test inputs, never rulebook
claims (ADR 0009 part a). The golden tables and P1-P8 are QA's (ST-022, ST-023).
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.sports.pickleball.rules import (
    DomainError,
    FaultKind,
    GameOver,
    GameState,
    IllegalState,
    RallyOutcome,
    Side,
    UnknownOutcome,
    apply,
    fold,
    new_game,
)
from tests.unit.sports.pickleball.rules_helpers import A, B, call, config, declared

pytestmark = [pytest.mark.unit, pytest.mark.scoring]


# ------------------------------------------------------------------ apply (§5 rows 1-7)


@pytest.mark.parametrize(
    "outcome",
    [
        RallyOutcome.won_by(A),
        RallyOutcome.won_by(B),
        RallyOutcome.replay(),
        RallyOutcome.fault(by=A, kind=FaultKind.NVZ),
    ],
)
def test_any_rally_on_a_finished_game_is_game_over(outcome: RallyOutcome) -> None:
    finished = apply(declared(10, 8, 1), RallyOutcome.won_by(A), config())
    assert isinstance(finished, GameState)
    assert finished.is_over
    result = apply(finished, outcome, config())
    assert isinstance(result, GameOver)
    assert isinstance(result, DomainError)
    assert result.message == "game already over"


def test_receiving_side_wins_at_server_one_passes_to_server_two_without_a_point() -> None:
    result = apply(declared(3, 5, 1), RallyOutcome.won_by(B), config())
    assert isinstance(result, GameState)
    assert result.serving_side is A
    assert call(result) == (3, 5, 2)


def test_receiving_side_wins_at_server_two_is_a_side_out_to_server_one() -> None:
    result = apply(declared(3, 5, 2), RallyOutcome.won_by(B), config())
    assert isinstance(result, GameState)
    assert result.serving_side is B
    assert call(result) == (5, 3, 1)


def test_serving_side_wins_scores_one_point_and_keeps_the_server() -> None:
    before = declared(7, 4, 1)
    result = apply(before, RallyOutcome.won_by(A), config())
    assert isinstance(result, GameState)
    assert call(result) == (8, 4, 1)
    assert result.server_player == before.server_player


def test_first_service_exception_side_out_after_one_lost_rally() -> None:
    start = new_game(config(first_service=True), A)
    result = apply(start, RallyOutcome.won_by(B), config(first_service=True))
    assert isinstance(result, GameState)
    assert result.serving_side is B
    assert call(result) == (0, 0, 1)


@pytest.mark.parametrize(
    ("target", "margin", "before", "over"),
    [
        (11, 2, (10, 8), True),
        (11, 2, (10, 10), False),
        (15, 2, (14, 12), True),
        (11, 1, (10, 10), True),
        (1, 1, (0, 0), True),
    ],
)
def test_game_ends_at_the_first_rally_meeting_target_and_margin(
    target: int, margin: int, before: tuple[int, int], over: bool
) -> None:
    cfg = config(target, margin)
    state = declared(*before, 1, points_to_win=target, win_by=margin)
    result = apply(state, RallyOutcome.won_by(A), cfg)
    assert isinstance(result, GameState)
    assert result.is_over is over
    assert result.winner is (A if over else None)


def test_replay_is_identity() -> None:
    state = declared(5, 5, 1)
    assert apply(state, RallyOutcome.replay(), config()) == state


@pytest.mark.parametrize("junk", [None, "A", Side.A, 3, object()])
def test_an_unknown_outcome_is_returned_as_an_error_never_raised(junk: Any) -> None:
    result = apply(declared(1, 1, 1), junk, config())
    assert isinstance(result, UnknownOutcome)


def test_a_state_inconsistent_with_doubles_config_is_illegal() -> None:
    singles_like = GameState(
        score_a=0,
        score_b=0,
        serving_side=A,
        server_number=None,
        winner=None,
        server_player="A1",
        right_court_a="A1",
        right_court_b="B1",
    )
    assert isinstance(apply(singles_like, RallyOutcome.won_by(A), config()), IllegalState)


def test_a_non_state_is_illegal_not_raised() -> None:
    assert isinstance(apply("0-0-2", RallyOutcome.won_by(A), config()), IllegalState)  # type: ignore[arg-type]


# ------------------------------------------------------------------ positions (SOD-05/06)


def test_server_two_is_the_partner_of_the_server_one() -> None:
    result = apply(declared(4, 2, 1), RallyOutcome.won_by(B), config())
    assert isinstance(result, GameState)
    assert result.server_player == "A2"
    assert result.right_court_player == {A: "A1", B: "B1"}


def test_scoring_switches_the_serving_pair_and_leaves_receivers() -> None:
    result = apply(declared(7, 4, 1), RallyOutcome.won_by(A), config())
    assert isinstance(result, GameState)
    assert result.server_player == "A1"
    assert result.right_court_player == {A: "A2", B: "B1"}


def test_side_out_hands_serve_to_the_right_court_player() -> None:
    state = apply(declared(7, 4, 1, side=B), RallyOutcome.won_by(B), config())  # B scores
    assert isinstance(state, GameState)
    assert state.right_court_player[B] == "B2"
    state = apply(state, RallyOutcome.won_by(A), config())
    state = apply(state, RallyOutcome.won_by(A), config())  # side-out to A
    assert isinstance(state, GameState)
    assert state.serving_side is A
    assert state.server_player == state.right_court_player[A]


# ------------------------------------------------------------------ faults (§5 Fault rows)


@pytest.mark.parametrize("kind", list(FaultKind))
@pytest.mark.parametrize("by", [A, B])
def test_every_fault_subtype_equals_the_faulting_side_losing_the_rally(
    kind: FaultKind, by: Side
) -> None:
    state = declared(4, 2, 1)
    assert apply(state, RallyOutcome.fault(by=by, kind=kind), config()) == apply(
        state, RallyOutcome.won_by(by.other), config()
    )


def test_serving_side_fault_at_server_one_passes_to_server_two() -> None:
    result = apply(declared(4, 2, 1), RallyOutcome.fault(by=A, kind=FaultKind.SERVE), config())
    assert isinstance(result, GameState)
    assert result.serving_side is A
    assert call(result) == (4, 2, 2)


# ------------------------------------------------------------------ fold (§5 fold rows)


def test_fold_of_nothing_is_the_start() -> None:
    start = new_game(config(), A)
    assert fold([], config(), start) == start


def test_fold_stops_at_the_first_domain_error() -> None:
    start = declared(10, 0, 1)
    result = fold([RallyOutcome.won_by(A), RallyOutcome.won_by(B)], config(), start)
    assert isinstance(result, GameOver)


def test_fold_returns_unknown_outcome_for_junk_in_the_list() -> None:
    start = new_game(config(), A)
    assert isinstance(fold([RallyOutcome.won_by(A), None], config(), start), UnknownOutcome)  # type: ignore[list-item]


_outcomes = st.one_of(
    st.sampled_from([A, B]).map(RallyOutcome.won_by),
    st.builds(
        lambda s, k: RallyOutcome.fault(by=s, kind=k),
        st.sampled_from([A, B]),
        st.sampled_from(list(FaultKind)),
    ),
    st.just(RallyOutcome.replay()),
)


@given(outcomes=st.lists(_outcomes, max_size=60), cut=st.integers(min_value=0, max_value=60))
def test_fold_equals_sequential_apply_and_prefix_then_suffix(
    outcomes: list[RallyOutcome], cut: int
) -> None:
    cfg = config(21, 2, first_service=True)
    start = new_game(cfg, A)
    state: GameState | DomainError = start
    for outcome in outcomes:
        assert isinstance(state, GameState)
        if state.is_over:
            break
        state = apply(state, outcome, cfg)
    played = outcomes  # fold must agree whether or not the game ended early
    whole = fold(played, cfg, start)
    if isinstance(state, GameState) and not state.is_over:
        assert whole == state
    middle = fold(played[:cut], cfg, start)
    if isinstance(middle, GameState):
        assert fold(played[cut:], cfg, middle) == whole


@given(
    junk=st.one_of(st.none(), st.integers(), st.text(max_size=3), st.sampled_from(list(Side))),
    outcome=_outcomes,
)
def test_apply_is_total(junk: Any, outcome: RallyOutcome) -> None:
    state = new_game(config(), A)
    for args in ((state, junk, config()), (junk, outcome, config()), (state, outcome, junk)):
        assert isinstance(apply(*args), GameState | DomainError)


def test_fold_from_a_non_state_is_illegal() -> None:
    assert isinstance(fold([], config(), None), IllegalState)  # type: ignore[arg-type]
