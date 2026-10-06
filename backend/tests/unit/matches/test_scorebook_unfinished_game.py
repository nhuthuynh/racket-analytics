"""PE-S2-R1-02: a correction that makes game n unfinished after game n+1 was started never
leaves the match without a way forward (match-aggregate I3, I7, §4 ``resolve``).

* Game n+1 has no rally yet: the next tag goes to game n, the first game that is not over in
  the projection (one source of truth for "the current game", I7). Before the fix it went to
  game n+1, was marked "needs your decision", and tag, resolve and start_game were all refused.
* Game n+1 already has rallies (C-03): they are marked; the player moves them back one by one,
  earliest first, with the provisional decision ``move_to_previous_game`` (match-aggregate §8
  Q1, owner pickleball-domain-coach, so ``needs_verification``). Audited, undoable.

Negative first.
"""

from __future__ import annotations

import pytest

from racket.matches.scorebook.domain import DecisionNeeded, OutcomeInput, RallyTimes
from racket.platform.errors import ValidationFailed
from tests.unit.matches.test_scorebook_corrections import Book, fresh

pytestmark = [pytest.mark.unit, pytest.mark.scoring]

GAME_1 = ["A"] * 11  # 11-0 to side A, rallies 1-11


def reopened(*game_2: str) -> Book:
    """Game 1 won 11-0, game 2 started (and tagged with ``game_2``), then rally 11 corrected
    to side B: game 1 is 10-0 and not over any more."""
    b = fresh(*GAME_1).start("B").tag(*game_2)
    return b.correct(11, "winning_side", "B")


def resolve(b: Book, n: int, decision: str) -> Book:
    b.b = b.b.resolve(b.ids[n - 1], decision, expected_version=b.v, ctx=b.ctx)
    return b


def codes(exc: pytest.ExceptionInfo[ValidationFailed]) -> list[tuple[str | None, str]]:
    return [(f.field, f.code) for f in exc.value.fields]


def test_the_next_tag_goes_to_the_unfinished_game_not_to_the_empty_next_game() -> None:
    b = reopened().tag("A")
    rows = b.sheet()["rows"]
    assert (rows[-1]["game"], rows[-1]["marker"]) == (1, None)
    assert all(r["marker"] is None for r in rows)


def test_after_the_unfinished_game_ends_tagging_continues_in_the_started_game() -> None:
    b = reopened()
    while not b.sheet()["games"][0]["winner"]:
        b.tag("A")
    b.tag("B")
    sheet = b.sheet()
    assert sheet["rows"][-1]["game"] == 2
    assert [r["marker"] for r in sheet["rows"]] == [None] * len(sheet["rows"])
    assert sheet["games"][0]["winner"] == "A"


@pytest.mark.needs_verification
def test_c03_rallies_block_new_tags_until_resolved() -> None:
    b = reopened("B", "B")
    rows = b.sheet()["rows"]
    assert [r["marker"] for r in rows[11:]] == ["needs_decision", "needs_decision"]
    with pytest.raises(DecisionNeeded):
        b.b.tag(
            RallyTimes.parse(99_000, 99_900),
            OutcomeInput.parse({"ending": "winner", "winning_side": "A"}, format="doubles"),
            ready=True,
            expected_version=b.v,
            ctx=b.ctx,
        )


@pytest.mark.needs_verification
def test_only_the_earliest_rally_of_a_game_moves_back() -> None:
    b = reopened("B", "B")
    with pytest.raises(ValidationFailed) as exc:
        resolve(b, 13, "move_to_previous_game")
    assert codes(exc) == [("decision", "not_first_in_game")]


@pytest.mark.needs_verification
def test_a_rally_cannot_move_back_into_a_game_that_is_over() -> None:
    """C-02 in game 2 (rallies past game 2's new end): game 1 is over, so they cannot move back;
    their choices stay withdraw or move to the next game."""
    b = fresh(*GAME_1).start("B").tag(*(["B"] * 10 + ["A", "B", "B", "B"]))
    b.correct(22, "winning_side", "B")  # game 2 now ends 11-0 at rally 22; 23-25 are marked
    assert b.sheet()["rows"][22]["marker"] == "needs_decision"
    with pytest.raises(ValidationFailed) as exc:
        resolve(b, 23, "move_to_previous_game")
    assert codes(exc) == [("decision", "previous_game_over")]


@pytest.mark.needs_verification
def test_a_game_1_rally_has_no_previous_game() -> None:
    b = fresh(*(["A"] * 10 + ["B", "A", "A", "A"])).correct(11, "winning_side", "A")
    with pytest.raises(ValidationFailed) as exc:
        resolve(b, 12, "move_to_previous_game")
    assert codes(exc) == [("decision", "no_previous_game")]


@pytest.mark.needs_verification
def test_move_to_previous_game_scores_the_rally_in_the_unfinished_game_and_undoes() -> None:
    b = reopened("B", "A")  # game-2 rallies 12 (B) and 13 (A); game 1 stands 0-10-1, B serving
    before = b.bytes()
    resolve(b, 12, "move_to_previous_game")  # B wins it in game 1: 1-10-1
    sheet = b.sheet()
    assert [(r["game"], r["marker"]) for r in sheet["rows"][11:]] == [
        (1, None),
        (2, "needs_decision"),  # game 1 is still not over
    ]
    assert sheet["rows"][11]["score_after"] == "1-10-1"
    assert sheet["rows"][11]["corrected_by_user"] is True
    change = b.b.changes[-1]
    assert (change.kind, change.field, change.old_value, change.new_value) == (
        "resolution",
        "game_number",
        2,
        1,
    )
    resolve(b, 13, "move_to_previous_game")  # now the earliest of game 2: moves back too
    assert [(r["game"], r["marker"]) for r in b.sheet()["rows"]] == [(1, None)] * 13
    b.tag("A")  # game 2 is empty again: the next tag goes to game 1 (still unfinished)
    assert b.sheet()["rows"][-1]["game"] == 1
    b.undo().undo().undo()
    assert b.bytes() == before
