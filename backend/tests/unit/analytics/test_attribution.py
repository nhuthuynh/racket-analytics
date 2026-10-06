"""Attribution conservation: every rally a side lost is attributed exactly once, to a category
or to "unattributed", per game, split into lost on serve and on receive (ST-045; FR-109;
ADR 0003).

sprint-03 §5 TDD order: 1. a rally attributed twice -> invariant error; 2. a lost rally
missing -> invariant error; 3. property: >= 1,000 generated matches (profile ``ci``),
attributed + unattributed = lost on serve and on receive, 0 violations. The check runs on every
stats computation.
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.analytics.attribution import (
    UNATTRIBUTED,
    AttributionBroken,
    attribute_lost_rallies,
    check_conservation,
    lost_rallies,
)
from racket.analytics.starter_stats import counted_rallies, starter_stats
from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game, sheet, side_a_wins_game, tag

pytestmark = pytest.mark.unit

SIDES = ("A", "B")


def _worked() -> list[Any]:
    return counted_rallies(one_game(WORKED_EXAMPLE))


# ---------------------------------------------------------------- 1. twice -> error
def test_a_rally_attributed_twice_breaks_the_invariant() -> None:
    counted = _worked()
    attributed = attribute_lost_rallies(counted)
    attributed["A"][1]["serve"]["unforced_error"].append(10)
    with pytest.raises(AttributionBroken, match="A game 1 serve"):
        check_conservation(counted, attributed)


def test_one_rally_in_two_categories_breaks_the_invariant() -> None:
    counted = _worked()
    attributed = attribute_lost_rallies(counted)
    attributed["A"][1]["serve"][UNATTRIBUTED] = [2]  # also under fault:serve
    with pytest.raises(AttributionBroken, match="A game 1 serve"):
        check_conservation(counted, attributed)


def test_a_rally_of_another_side_or_phase_breaks_the_invariant() -> None:
    counted = _worked()
    attributed = attribute_lost_rallies(counted)
    attributed["A"][1]["receive"][UNATTRIBUTED].append(1)  # A won rally 1
    with pytest.raises(AttributionBroken, match="A game 1 receive"):
        check_conservation(counted, attributed)


# ---------------------------------------------------------------- 2. missing -> error
def test_a_lost_rally_left_out_breaks_the_invariant() -> None:
    counted = _worked()
    attributed = attribute_lost_rallies(counted)
    attributed["B"][1]["receive"] = {}
    with pytest.raises(AttributionBroken, match="B game 1 receive"):
        check_conservation(counted, attributed)


def test_a_missing_game_breaks_the_invariant() -> None:
    counted = _worked()
    attributed = attribute_lost_rallies(counted)
    del attributed["A"][1]
    with pytest.raises(AttributionBroken, match="A game 1"):
        check_conservation(counted, attributed)


# ---------------------------------------------------------------- the worked example
def test_the_worked_example_splits_lost_rallies_by_serve_and_receive() -> None:
    lost = lost_rallies(_worked())
    assert lost["A"][1] == {"serve": [2, 10, 12], "receive": [3, 4, 13, 14]}
    assert lost["B"][1] == {"serve": [5, 6], "receive": [1, 7, 9, 11]}


def test_own_endings_are_their_category_and_opponent_winners_are_unattributed() -> None:
    attributed = attribute_lost_rallies(_worked())
    assert attributed["A"][1]["serve"] == {"fault:serve": [2, 12], "unforced_error": [10]}
    assert attributed["A"][1]["receive"] == {"unforced_error": [4], UNATTRIBUTED: [3, 13, 14]}
    assert attributed["B"][1]["serve"] == {"forced_error": [5], "fault:nvz": [6]}
    assert attributed["B"][1]["receive"] == {
        "unforced_error": [9],
        "fault:untagged": [11],
        UNATTRIBUTED: [1, 7],
    }


def test_the_fr_109_example_14_lost_6_on_serve_and_8_on_receive() -> None:
    a_wins, b_wins = tag("A", "winner"), tag("B", "winner")
    tags = [
        tag("B", "unforced_error"),  # A loses on serve (0-0-2) -> B serves
        *[b_wins] * 8,  # A loses 8 on receive, 8-0 B
        a_wins, a_wins,  # B server 2, then A serves
        b_wins, b_wins,  # A loses 2 on serve
        a_wins, a_wins,
        b_wins, b_wins,  # A loses 2 on serve
        a_wins, a_wins,
        b_wins,  # A loses 1 on serve
    ]  # fmt: skip
    counted = counted_rallies(one_game(tags))
    lost = lost_rallies(counted)["A"][1]
    assert (len(lost["serve"]), len(lost["receive"])) == (6, 8)
    attributed = attribute_lost_rallies(counted)
    check_conservation(counted, attributed)
    totals = {p: sum(len(v) for v in attributed["A"][1][p].values()) for p in lost}
    assert totals == {"serve": 6, "receive": 8}


def test_games_are_kept_apart() -> None:
    played = sheet(
        [
            {"first_serving_side": "A", "tags": side_a_wins_game()},
            {"first_serving_side": "B", "tags": [tag("A", "winner"), tag("B", "fault", "foot")]},
        ]
    )
    lost = lost_rallies(counted_rallies(played))
    assert lost["B"][1] == {"serve": [], "receive": list(range(1, 12))}
    assert lost["B"][2] == {"serve": [12], "receive": []}
    assert lost["A"][2] == {"serve": [13], "receive": []}  # A won the serve in rally 12


# ---------------------------------------------------------------- checked on every computation
def test_starter_stats_runs_the_check(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    import racket.analytics.starter_stats as module

    real = module.check_conservation

    def spy(counted: Any, attributed: Any) -> None:
        calls.append(len(counted))
        real(counted, attributed)

    monkeypatch.setattr(module, "check_conservation", spy)
    starter_stats(one_game(WORKED_EXAMPLE))
    assert calls == [13]


# ---------------------------------------------------------------- 3. property (>= 1,000 in ci)
ENDINGS = st.sampled_from(["winner", "unforced_error", "forced_error", "fault", "replay"])


@st.composite
def a_tag(draw: st.DrawFn) -> dict[str, Any]:
    ending = draw(ENDINGS)
    if ending == "replay":
        return tag(None, ending)
    side = draw(st.sampled_from(SIDES))
    kind = draw(st.sampled_from([None, "serve", "nvz", "foot"])) if ending == "fault" else None
    return tag(side, ending, kind)


@st.composite
def a_match(draw: st.DrawFn) -> dict[str, Any]:
    games = draw(st.integers(min_value=1, max_value=3))
    return sheet(
        [
            {
                "first_serving_side": draw(st.sampled_from(SIDES)),
                "tags": draw(st.lists(a_tag(), max_size=30)),
            }
            for _ in range(games)
        ]
    )


@given(a_match())
def test_property_every_lost_rally_is_attributed_once(played: dict[str, Any]) -> None:
    counted = counted_rallies(played)
    attributed = attribute_lost_rallies(counted)
    check_conservation(counted, attributed)
    lost = lost_rallies(counted)
    for side in SIDES:
        total_lost = sum(len(p) for g in lost[side].values() for p in g.values())
        assert total_lost == sum(r.winning_side != side for r in counted)
        for game, phases in lost[side].items():
            for phase in ("serve", "receive"):
                got = sorted(n for v in attributed[side][game][phase].values() for n in v)
                assert got == phases[phase]


def test_an_attributed_game_that_was_never_played_breaks_the_invariant() -> None:
    counted = _worked()
    attributed = attribute_lost_rallies(counted)
    attributed["B"][2] = {"serve": {}, "receive": {}}
    with pytest.raises(AttributionBroken, match="B game 2: attributed but never played"):
        check_conservation(counted, attributed)
