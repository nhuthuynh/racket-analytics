"""PE-S2-R1-04 (match-aggregate I5 "rallies ordered by start_ms"): rallies of different games
keep the order of the games on the video. A rally of game g starts after every kept rally of
the games before g ends, and ends before every kept rally of the games after g starts; else
422 ``invalid_rally`` with ``start_ms``/``out_of_game_order``. Inside one game a rally may be
tagged before another (a missed rally filled in later); the sheet sorts it by ``start_ms``.

Negative first: a tag, then a times correction, out of game order; then the controls.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from racket.matches.scorebook.domain import InvalidRally, OutcomeInput, RallyTimes
from tests.unit.matches.test_scorebook_corrections import Book, fresh

pytestmark = [pytest.mark.unit, pytest.mark.scoring]

WIN_A = {"ending": "winner", "winning_side": "A"}
# Game 1 is won 11-0 by side A: rallies at 0-900, 1000-1900, ..., 10000-10900 ms.
GAME_1 = ["A"] * 11


def game_2_started() -> Book:
    return fresh(*GAME_1).start("B")


def tag_at(b: Book, start: int, end: int) -> Book:
    b.b, rally = b.b.tag(
        RallyTimes.parse(start, end),
        OutcomeInput.parse(WIN_A, format="doubles"),
        ready=True,
        expected_version=b.v,
        ctx=b.ctx,
    )
    b.ids.append(rally.id)
    return b


def codes(exc: pytest.ExceptionInfo[InvalidRally]) -> list[tuple[str | None, str]]:
    return [(f.field, f.code) for f in exc.value.fields]


def test_a_game_2_tag_inside_game_1_time_span_is_refused() -> None:
    b = game_2_started()
    before = b.b
    with pytest.raises(InvalidRally) as exc:
        tag_at(b, 950, 990)  # in the gap between game-1 rallies 1 and 2: no overlap
    assert codes(exc) == [("start_ms", "out_of_game_order")]
    assert b.b is before  # nothing changed


def test_a_times_correction_keeps_a_rally_out_of_game_order_refused() -> None:
    """A one-field times correction of an ordered sheet cannot jump a game without first
    overlapping a rally, so the case is stored data written before this check (the PE probe):
    a game-2 rally at 950-990. Correcting its end keeps it out of order: refused."""
    b = game_2_started()
    legacy = tag_at(fresh(*GAME_1).start("B"), 20_000, 20_900).b.rallies[-1]
    moved = replace(legacy, times=RallyTimes.parse(950, 990))
    b.b = replace(b.b, rallies=(*b.b.rallies, moved), version=b.v + 1)
    b.ids.append(moved.id)
    with pytest.raises(InvalidRally) as exc:
        b.correct(12, "end_ms", 995)
    assert codes(exc) == [("start_ms", "out_of_game_order")]


def test_a_times_correction_that_jumps_a_game_overlaps_first() -> None:
    b = tag_at(game_2_started(), 20_000, 20_900)
    with pytest.raises(InvalidRally) as exc:
        b.correct(12, "start_ms", 950)
    assert codes(exc) == [("start_ms", "overlaps_rally")]
    b.correct(12, "start_ms", 11_000)  # control: still after game 1, accepted
    b.correct(11, "end_ms", 10_950)  # control: game 1's last rally still before game 2


def test_controls_a_later_game_2_tag_and_an_earlier_tag_inside_the_same_game() -> None:
    b = tag_at(game_2_started(), 20_000, 20_900)
    tag_at(b, 15_000, 15_900)  # game 2, before the other game-2 rally: same game, accepted
    rows = b.sheet()["rows"]
    assert [(r["game"], r["start_ms"]) for r in rows[11:]] == [(2, 15_000), (2, 20_000)]
    assert [r["number"] for r in rows] == list(range(1, 14))
