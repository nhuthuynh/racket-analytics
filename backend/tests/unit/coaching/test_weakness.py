"""ST-055 unit (FR-120, FR-109; ADR 0003; COACH-4 weakness catalogue; coaching-plan §3).

The pure domain ``racket.coaching.weakness.domain``: catalogue cells (§2), points conceded (§3),
ranking and tie-break (§4), primary metric and plan target (§5), the worked examples of §7
(FR-120, metric dictionary §2, GS-AN-1 gm1..gm3 per side) and the conservation property
(>= 1,000 examples). Negative cases first.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from racket.analytics.public import facts_of_sheet
from racket.coaching.weakness import acl
from racket.coaching.weakness.domain import (
    CATALOGUE,
    NO_TAGGED_MATCH,
    UNATTRIBUTED,
    UNIT,
    RallyFact,
    WeaknessConservationBroken,
    attribute,
    check_conservation,
    rank,
)
from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game
from tests.unit.coaching.weakness_examples import (
    GOLDEN,
    catalogue_rows,
    golden_sheet,
    render,
)

pytestmark = [pytest.mark.coaching]

MATCH = uuid.UUID(int=1)
OTHER = {"A": "B", "B": "A"}


def fact(
    number: int,
    serving: str,
    winning: str,
    ending: str,
    kind: str | None = None,
    *,
    game: int = 1,
    player: str | None = None,
    point_to: str | bool | None = True,
) -> RallyFact:
    """A counted rally; by default the point follows side-out (only the server scores)."""
    if point_to is True:
        point_to = winning if winning == serving else None
    return RallyFact(
        rally_id=f"r{number}",
        game=game,
        serving_side=serving,
        winning_side=winning,
        ending=ending,
        fault_kind=kind,
        responsible_player=player,
        point_to=point_to if isinstance(point_to, str) else None,
    )


def ranked(facts: list[RallyFact], side: str = "A", games: int = 1):  # type: ignore[no-untyped-def]
    return rank(attribute(MATCH, side, facts), games, rallies=len(facts))


# ------------------------------------------------------------------ negative cases first
def test_zero_games_give_an_empty_ranking_with_a_reason_not_an_error() -> None:
    ranking = rank((), 0, rallies=0)
    assert ranking.weaknesses == ()
    assert ranking.reason == NO_TAGGED_MATCH == "no_tagged_match"
    assert (ranking.games, ranking.rallies, ranking.unattributed) == (0, 0, 0)
    assert ranking.unit == UNIT
    assert ranking.provisional is True


def test_lost_rallies_without_games_are_refused() -> None:
    losses = attribute(MATCH, "A", [fact(1, "A", "B", "unforced_error")])
    with pytest.raises(ValueError, match="games"):
        rank(losses, 0, rallies=1)


def test_a_side_other_than_a_or_b_is_refused() -> None:
    with pytest.raises(ValueError, match="side"):
        attribute(MATCH, "C", [fact(1, "A", "B", "winner")])


def test_a_lost_rally_left_out_breaks_conservation() -> None:
    facts = [fact(1, "A", "B", "unforced_error"), fact(2, "B", "B", "winner")]
    losses = attribute(MATCH, "A", facts)
    with pytest.raises(WeaknessConservationBroken, match="game 1 receive"):
        check_conservation(MATCH, "A", facts, losses[:1])


def test_a_lost_rally_counted_twice_breaks_conservation() -> None:
    facts = [fact(1, "A", "B", "unforced_error")]
    losses = attribute(MATCH, "A", facts)
    with pytest.raises(WeaknessConservationBroken, match="game 1 serve"):
        check_conservation(MATCH, "A", facts, losses + losses)


def test_a_rally_moved_to_the_other_phase_breaks_conservation() -> None:
    facts = [fact(1, "A", "B", "unforced_error")]
    (loss,) = attribute(MATCH, "A", facts)
    moved = replace(loss, phase="receive")
    with pytest.raises(WeaknessConservationBroken, match="serve"):
        check_conservation(MATCH, "A", facts, (moved,))


def test_rallies_the_side_won_are_not_losses() -> None:
    assert attribute(MATCH, "A", [fact(1, "A", "A", "winner"), fact(2, "B", "A", "fault")]) == ()


# ------------------------------------------------------------------ catalogue §2 cells
@pytest.mark.parametrize(
    ("ending", "kind", "weakness"),
    [
        ("unforced_error", None, "unforced_errors"),
        ("fault", "serve", "serve_faults"),
        ("fault", "nvz", "other_faults"),
        ("fault", "two_bounce", "other_faults"),
        ("fault", "foot", "other_faults"),
        ("fault", "other", "other_faults"),
        ("fault", None, "other_faults"),
        ("forced_error", None, "errors_under_pressure"),
        ("winner", None, "opponent_winners"),
        ("let", None, UNATTRIBUTED),
    ],
)
def test_each_ending_of_a_lost_rally_goes_to_one_catalogue_cell(
    ending: str, kind: str | None, weakness: str
) -> None:
    for serving in "AB":
        (loss,) = attribute(MATCH, "A", [fact(1, serving, "B", ending, kind)])
        assert loss.category == weakness
        assert loss.phase == ("serve" if serving == "A" else "receive")


def test_the_responsible_player_never_changes_the_cell() -> None:
    a = attribute(MATCH, "A", [fact(1, "A", "B", "unforced_error", player="A1")])
    b = attribute(MATCH, "A", [fact(1, "A", "B", "unforced_error", player="A2")])
    assert a[0].category == b[0].category == "unforced_errors"
    assert (a[0].responsible_player, b[0].responsible_player) == ("A1", "A2")


def test_the_catalogue_order_and_names() -> None:
    assert [(e.id, e.name, e.order) for e in CATALOGUE] == [
        ("unforced_errors", "Unforced errors", 1),
        ("serve_faults", "Serve faults", 2),
        ("other_faults", "Other faults", 3),
        ("errors_under_pressure", "Errors under pressure", 4),
        ("opponent_winners", "Opponent winners against you", 5),
    ]


# ------------------------------------------------------------------ §3 points conceded
def test_points_conceded_follow_the_sheet_not_the_phase() -> None:
    # under side-out a loss on serve concedes nothing; a sheet that scored it (rally scoring)
    # concedes the point: the product reads who scored, never a rule
    side_out = ranked([fact(1, "A", "B", "unforced_error"), fact(2, "B", "B", "unforced_error")])
    rally = ranked([fact(1, "A", "B", "unforced_error", point_to="B")])
    assert side_out.weaknesses[0].conceded == 1
    assert rally.weaknesses[0].conceded == 1
    assert rally.weaknesses[0].lost_on_serve == 1


def test_points_conceded_never_change_the_order() -> None:
    # 3 losses on serve (0 points) outrank 2 on receive (2 points)
    facts = [fact(n, "A", "B", "fault", "nvz") for n in (1, 2, 3)]
    facts += [fact(n, "B", "B", "unforced_error") for n in (4, 5)]
    ranking = ranked(facts)
    assert [(w.id, w.conceded) for w in ranking.weaknesses] == [
        ("other_faults", 0),
        ("unforced_errors", 2),
    ]


# ------------------------------------------------------------------ §4 ranking and unit
def test_equal_counts_keep_the_catalogue_order() -> None:
    facts = [
        fact(1, "B", "B", "winner"),
        fact(2, "A", "B", "forced_error"),
        fact(3, "A", "B", "fault", "nvz"),
        fact(4, "A", "B", "fault", "serve"),
        fact(5, "A", "B", "unforced_error"),
    ]
    ranking = ranked(facts)
    assert [w.id for w in ranking.weaknesses] == [e.id for e in CATALOGUE]
    assert [w.rank for w in ranking.weaknesses] == [1, 2, 3, 4, 5]


def test_weaknesses_with_no_rally_lost_are_not_listed() -> None:
    ranking = ranked([fact(1, "A", "B", "unforced_error"), fact(2, "A", "A", "winner")])
    assert [w.id for w in ranking.weaknesses] == ["unforced_errors"]


def test_per_game_values_are_exact_fractions() -> None:
    facts = [fact(n, "A", "B", "unforced_error") for n in range(5)]
    facts += [fact(9, "B", "B", "unforced_error")]
    (w,) = ranked(facts, games=3).weaknesses
    assert (w.per_game, w.on_serve_per_game, w.on_receive_per_game) == (
        Fraction(2),
        Fraction(5, 3),
        Fraction(1, 3),
    )
    assert w.conceded_per_game == Fraction(1, 3)
    assert w.games == 3


def test_the_ranking_carries_the_provisional_unit() -> None:
    ranking = ranked([fact(1, "A", "B", "unforced_error")])
    assert ranking.unit == "rallies_lost_per_game"
    assert (ranking.provisional, ranking.side_out_verified) == (True, False)
    assert ranking.reason is None
    verified = rank((), 1, rallies=0, side_out_verified=True)
    assert verified.provisional is False


def test_skipped_matches_are_carried() -> None:
    assert rank((), 0, rallies=0, skipped_matches=2).skipped_matches == 2


# ------------------------------------------------------------------ §5 primary metric
@pytest.mark.parametrize(
    ("facts", "metric", "target"),
    [
        ([("A", "fault", "serve")], "AN-05", "AN-05"),
        ([("B", "fault", "serve")], "AN-07", "AN-07:fault"),
        ([("A", "fault", "serve"), ("B", "fault", "serve")], "AN-05", "AN-05"),
        ([("A", "winner", None)], "AN-01", "AN-01"),
        ([("B", "winner", None)], "AN-02", "AN-02"),
        ([("A", "winner", None), ("B", "winner", None)], "AN-01", "AN-01"),
        ([("B", "unforced_error", None)], "AN-04", "AN-04"),
        ([("A", "fault", None)], "AN-07", "AN-07:fault"),
        ([("A", "forced_error", None)], "AN-07", "AN-07:forced-error"),
    ],
)
def test_the_primary_metric_and_plan_target(
    facts: list[tuple[str, str, str | None]], metric: str, target: str
) -> None:
    ranking = ranked([fact(n, s, "B", e, k) for n, (s, e, k) in enumerate(facts)])
    (w,) = ranking.weaknesses
    assert (w.metric_id, w.plan_target) == (metric, target)


# ------------------------------------------------------------------ §7 worked examples
def test_the_catalogue_has_every_worked_example() -> None:
    rows = catalogue_rows()
    assert set(rows) == {("FR-120", "Ivy")} | {
        (name, side) for name in ("dict §2", *GOLDEN) for side in "AB"
    }


@pytest.mark.weakness_golden
def test_the_fr_120_example_equals_the_catalogue() -> None:
    facts = [fact(n, "A", "B", "unforced_error") for n in range(10)]
    facts += [fact(10 + n, "B", "B", "fault", "serve") for n in range(4)]
    games, cell, totals = catalogue_rows()[("FR-120", "Ivy")]
    ranking = ranked(facts, games=games)
    assert render(ranking) == (cell, totals)
    assert [w.name for w in ranking.weaknesses] == ["Unforced errors", "Serve faults"]


@pytest.mark.weakness_golden
@pytest.mark.parametrize("side", ["A", "B"])
def test_the_metric_dictionary_example_equals_the_catalogue(side: str) -> None:
    games, cell, totals = catalogue_rows()[("dict §2", side)]
    facts = facts_of_sheet(one_game(WORKED_EXAMPLE))
    translated = acl.translate(facts)
    ranking = rank(attribute(MATCH, side, translated), len(facts.games), rallies=len(translated))
    assert len(facts.games) == games
    assert render(ranking) == (cell, totals)


@pytest.mark.weakness_golden
@pytest.mark.parametrize("side", ["A", "B"])
@pytest.mark.parametrize("name", list(GOLDEN))
def test_the_golden_matches_equal_the_catalogue_per_side(name: str, side: str) -> None:
    games, cell, totals = catalogue_rows()[(name, side)]
    facts = facts_of_sheet(golden_sheet(name))
    translated = acl.translate(facts)
    ranking = rank(attribute(MATCH, side, translated), len(facts.games), rallies=len(translated))
    assert len(facts.games) == games
    assert render(ranking) == (cell, totals)


# ------------------------------------------------------------------ conservation property
_SIDE = st.sampled_from("AB")
_ENDING = st.sampled_from(["winner", "unforced_error", "forced_error", "fault", "let"])
_KIND = st.sampled_from([None, "serve", "nvz", "two_bounce", "foot", "other"])
_RALLY = st.tuples(st.integers(1, 3), _SIDE, _SIDE, _ENDING, _KIND, st.booleans())


# Examples come from the Hypothesis profile: >= 1,000 on `ci` (CI property step, G04-03 c),
# the default profile in the 10 s domain step (SRE-VERIFY04R3-03, ADR 0049).
@settings(deadline=None)
@given(rallies=st.lists(_RALLY, max_size=60), side=_SIDE)
def test_every_lost_rally_is_attributed_once_per_game_and_phase(
    rallies: list[tuple[int, str, str, str, str | None, bool]], side: str
) -> None:
    facts = [
        fact(n, srv, win, ending, kind if ending == "fault" else None, game=game,
             point_to=win if (scored or win == srv) else None)
        for n, (game, srv, win, ending, kind, scored) in enumerate(rallies)
    ]  # fmt: skip
    losses = attribute(MATCH, side, facts)
    check_conservation(MATCH, side, facts, losses)  # never raises on the product's attribution
    games = len({f.game for f in facts})
    ranking = rank(losses, games, rallies=len(facts))
    lost = [f for f in facts if f.winning_side == OTHER[side]]
    on_serve = sum(1 for f in lost if f.serving_side == side)
    assert (ranking.lost_on_serve, ranking.lost_on_receive) == (on_serve, len(lost) - on_serve)
    assert sum(w.lost for w in ranking.weaknesses) + ranking.unattributed == len(lost)
    assert sum(w.lost_on_serve for w in ranking.weaknesses) <= on_serve
    for w in ranking.weaknesses:
        assert w.lost == w.lost_on_serve + w.lost_on_receive > 0
        assert w.conceded <= w.lost
    keys = [(-w.lost, w.catalogue_order) for w in ranking.weaknesses]
    assert keys == sorted(keys)
    if games == 0:
        assert ranking.reason == NO_TAGGED_MATCH
