"""Property suite P1-P8 for the rules engine (ST-022; QD §2.3; NFR-002a).

Stated for ANY valid side-out doubles configuration, so they make no rulebook claim (ADR 0009,
sprint-01 §14.2). Hypothesis profile ``ci`` runs >= 1,000 random rally sequences per property
per CI run (``HYPOTHESIS_PROFILE=ci``); the edit-time ``dev`` profile runs 100.

Written before the engine: RED until ST-020 (seams in tests/support/contract.py, ADR 0012).
P3 is rally scoring, which is blocked (FR-043, OQ-01): it is skipped with that reason and listed
in docs/sprints/01/test-plan-status.md.
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests.support import scoring as sc

pytestmark = [pytest.mark.scoring]

_side = st.sampled_from("AB")
_raw_outcome = st.one_of(
    st.tuples(st.just("won"), _side),
    st.tuples(st.just("fault"), _side, st.sampled_from(sc.FAULT_NAMES)),
    st.just(("replay",)),
)
sequences = st.lists(_raw_outcome, max_size=150)
configs = st.fixed_dictionaries(
    {
        "points_to_win": st.integers(min_value=1, max_value=30),
        "win_by": st.integers(min_value=1, max_value=3),
        "first_service": st.booleans(),
    }
)


@pytest.fixture(autouse=True)
def _engine_present() -> None:
    """Fail fast (and RED with the story) before Hypothesis starts generating examples."""
    sc.contract.RULES_MODULE.load()


def _config(raw: dict[str, Any]) -> Any:
    return sc.mechanics_config(
        raw["points_to_win"], raw["win_by"], first_service=raw["first_service"]
    )


def _check(seq: list[tuple[str, ...]], cfg: dict[str, Any], first: str, prop: str) -> list[Any]:
    return sc.check_invariants(seq, _config(cfg), first, props=frozenset({prop}))


@given(seq=sequences, cfg=configs, first=_side)
def test_p1_scores_never_decrease_and_rise_by_at_most_one(seq, cfg, first) -> None:  # type: ignore[no-untyped-def]
    _check(seq, cfg, first, "P1")


@given(seq=sequences, cfg=configs, first=_side)
def test_p2_side_out_only_the_serving_side_scores(seq, cfg, first) -> None:  # type: ignore[no-untyped-def]
    _check(seq, cfg, first, "P2")


@pytest.mark.skip(
    reason="P3 is rally scoring: blocked on FR-043 / OQ-01 (sprint-01 §14.2); "
    "test-plan-status.md lists it"
)
def test_p3_rally_scoring_every_counted_rally_scores() -> None:
    raise AssertionError("not written until rally scoring is Ready")


@given(seq=sequences, cfg=configs, first=_side)
def test_p4_server_number_and_side_out_rotation(seq, cfg, first) -> None:  # type: ignore[no-untyped-def]
    _check(seq, cfg, first, "P4")


@given(seq=sequences, cfg=configs, first=_side)
def test_p5_game_over_exactly_at_the_first_rally_meeting_target_and_margin(seq, cfg, first) -> None:  # type: ignore[no-untyped-def]
    _check(seq, cfg, first, "P5")


@given(seq=sequences, cfg=configs, first=_side)
def test_p6_fold_equals_sequential_apply_and_prefix_then_suffix(seq, cfg, first) -> None:  # type: ignore[no-untyped-def]
    config = _config(cfg)
    states = sc.check_invariants(seq, config, first, props=frozenset())
    sc.check_fold(seq, config, states)


@given(seq=sequences, cfg=configs, first=_side)
def test_p7_fault_subtype_never_changes_the_state(seq, cfg, first) -> None:  # type: ignore[no-untyped-def]
    _check(seq, cfg, first, "P7")


@given(seq=sequences, cfg=configs, first=_side)
def test_p8_replay_is_identity(seq, cfg, first) -> None:  # type: ignore[no-untyped-def]
    _check(seq, cfg, first, "P8")


@given(seq=sequences, cfg=configs, first=_side)
def test_every_rally_after_game_over_is_refused(seq, cfg, first) -> None:  # type: ignore[no-untyped-def]
    """QD-RE-05 / SOD-12 for any config: check_invariants asserts GameOver past the end."""
    config = _config(cfg)
    states = sc.check_invariants(seq, config, first, props=frozenset())
    if states[-1].is_over:
        for outcome in sc.all_outcomes():
            assert isinstance(sc.apply(states[-1], outcome, config), sc.contract.GAME_OVER.load())
