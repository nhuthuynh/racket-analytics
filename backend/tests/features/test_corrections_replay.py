"""Binds tests/features/corrections_replay.feature, sprint-02 §7.4 (ST-041 for ST-032; QD C rows).

Runs on the pure scorebook (``Scorebook`` commands and ``project``; seams in
tests/support/contract.py). Expected scores come from the harness's independent side-out
stepper ``scripts/measure/taglib.py`` (neither the product engine nor the oracle), so a
re-scoring defect cannot hide behind the engine checking itself.

Fixtures (first serving side A, every rally ends "winner", no responsible player):
* C-01/C-04: 30 rallies ``C01_WINNERS``; the game does not end before or after the flip of
  rally 5 (10-7-1 before, 9-8-1 after; found by a seeded search with taglib).
* C-02: the harness conflict game ``taglib.CONFLICT_TAGS`` (A wins 11-0 at rally 14; rally 11
  was a side-out). Changing rally 11 to A ends the game at rally 11.
* C-03: game 1 ``C03_GAME1`` won 11-3 by A at rally 22, game 2 (B serves first) 5 rallies.
"""

from __future__ import annotations

import itertools
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import contract
from tests.support.scorebook import taglib

pytestmark = pytest.mark.scoring

scenarios("corrections_replay.feature")

C01_WINNERS = "BABBBABABABABBABAAAAAABABBBBBB"
C03_GAME1 = "AAAAABBBABABBAAAABAAAA"
C03_GAME2 = "ABABA"
COMPARED = ("number", "game", "serving_side", "server", "score_before", "score_after",
            "winning_side", "ending", "marker")  # fmt: skip


class Book:
    """A scorebook driven through its commands, with the version the client would send."""

    def __init__(self) -> None:
        self.ids = (uuid.UUID(int=i) for i in itertools.count(1))
        self.ctx = contract.SCOREBOOK_CONTEXT.load()(
            actor_id=uuid.UUID(int=0), at=datetime(2026, 11, 2, tzinfo=UTC), new_id=self._id
        )
        self.book = contract.SCOREBOOK.load().new(
            rules_version=contract.PROVISIONAL_PRESET, format="doubles", best_of=3
        )
        self.rally_ids: list[uuid.UUID] = []
        self.clock_ms = 0

    def _id(self) -> uuid.UUID:
        return next(self.ids)

    def start(self, side: str) -> None:
        side_obj = contract.RULES_SIDE.load()[side]
        self.book = self.book.start_game(
            first_serving_side=side_obj, ends_switched=False, ready=True,
            expected_version=self.book.version, ctx=self.ctx,
        )  # fmt: skip

    def tag(self, winners: str) -> None:
        times, outcome = contract.RALLY_TIMES.load(), contract.OUTCOME_INPUT.load()
        for w in winners:
            parsed = outcome.parse({"ending": "winner", "winning_side": w}, format="doubles")
            span = times.parse(self.clock_ms, self.clock_ms + 3_000)
            self.clock_ms += 4_000
            self.book, rally = self.book.tag(
                span, parsed, ready=True, expected_version=self.book.version, ctx=self.ctx
            )
            self.rally_ids.append(rally.id)

    def correct_winner(self, number: int, side: str) -> None:
        self.book = self.book.correct(
            self.rally_ids[number - 1], "winning_side", side,
            expected_version=self.book.version, ctx=self.ctx,
        )  # fmt: skip

    def undo(self) -> None:
        self.book = self.book.undo(expected_version=self.book.version, ctx=self.ctx)

    def sheet(self) -> dict[str, Any]:
        sheet: dict[str, Any] = contract.PROJECT.load()(self.book)
        return sheet

    def canonical(self) -> bytes:
        data: bytes = contract.CANONICAL_BYTES.load()(self.sheet())
        return data


def _flip(winners: str, number: int) -> str:
    i = number - 1
    return winners[:i] + ("A" if winners[i] == "B" else "B") + winners[i + 1 :]


def _tags(winners: str) -> list[dict[str, Any]]:
    return [
        {"winning_side": w, "ending": "winner", "responsible_player": None, "fault_kind": None}
        for w in winners
    ]


def _rows(sheet: dict[str, Any], fields: tuple[str, ...] = COMPARED) -> list[dict[str, Any]]:
    return [{f: row.get(f) for f in fields} for row in sheet["rows"]]


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


# ------------------------------------------------------------------ Given
@given("a tagged game with 30 rallies")
def thirty_rallies(state: dict[str, Any]) -> None:
    book = Book()
    book.start("A")
    book.tag(C01_WINNERS)
    state["book"], state["winners"] = book, C01_WINNERS
    assert taglib.game_winner(_tags(C01_WINNERS), "A") is None


@given("Ivy changed the winner of rally 5 of 30")
def changed_rally_5(state: dict[str, Any]) -> None:
    thirty_rallies(state)
    state["before"] = state["book"].canonical()
    state["book"].correct_winner(5, _flip(C01_WINNERS, 5)[4])
    assert state["book"].canonical() != state["before"], "the correction changed nothing"


@given("a tagged game that side A won 11-0 after 14 rallies")
def conflict_game(state: dict[str, Any]) -> None:
    winners = "".join(t["winning_side"] for t in taglib.CONFLICT_TAGS)
    book = Book()
    book.start("A")
    book.tag(winners)
    sheet = book.sheet()
    assert sheet["games"][0]["winner"] == "A"
    assert (sheet["games"][0]["score_a"], sheet["games"][0]["score_b"]) == (11, 0)
    assert len(sheet["rows"]) == 14
    state["book"], state["winners"] = book, winners


@given("game 1 was won by side A at rally 22 and game 2 has 5 tagged rallies")
def two_games(state: dict[str, Any]) -> None:
    book = Book()
    book.start("A")
    book.tag(C03_GAME1)
    assert book.sheet()["games"][0]["winner"] == "A"
    book.start("B")
    book.tag(C03_GAME2)
    state["book"] = book


# ------------------------------------------------------------------ When
@when("Ivy changes the winner of rally 5")
def change_rally_5(state: dict[str, Any]) -> None:
    state["before_sheet"] = state["book"].sheet()
    state["corrected"] = _flip(state["winners"], 5)
    state["book"].correct_winner(5, state["corrected"][4])


@when("she undoes that change")
def undo_change(state: dict[str, Any]) -> None:
    state["book"].undo()


@when(parsers.parse('Ivy changes rally {number:d} to "won by side {side}"'))
def change_rally(state: dict[str, Any], number: int, side: str) -> None:
    state["book"].correct_winner(number, side)


# ------------------------------------------------------------------ Then
@then("rallies 5 to 30 show scores recomputed from the corrected outcomes")
def rescored(state: dict[str, Any]) -> None:
    expected = taglib.expected_rows(_tags(state["corrected"]), first_serving_side="A")
    actual = state["book"].sheet()
    got = _rows(actual, tuple(taglib.ROW_FIELDS))
    assert taglib.compare_rows(expected, got) == []
    before = _rows(state["before_sheet"])
    after = _rows(actual)
    assert before[:4] == after[:4], "rallies before the correction must not change"
    assert before[4]["score_after"] != after[4]["score_after"], "rally 5 was not re-scored"
    assert actual["rows"][4]["corrected_by_user"] is True


@then("the score sheet matches one built from scratch with the corrected outcomes")
def equals_fresh_fold(state: dict[str, Any]) -> None:
    fresh = Book()
    fresh.start("A")
    fresh.tag(state["corrected"])
    corrected, scratch = state["book"].sheet(), fresh.sheet()
    assert _rows(corrected) == _rows(scratch)
    assert corrected["games"] == scratch["games"]
    assert corrected["match_winner"] == scratch["match_winner"]


@then("the score sheet is identical to the one before the change")
def byte_identical(state: dict[str, Any]) -> None:
    assert state["book"].canonical() == state["before"]


@then(parsers.parse("the game shows as won by side {side} at rally {number:d}"))
def won_at(state: dict[str, Any], side: str, number: int) -> None:
    sheet = state["book"].sheet()
    assert sheet["games"][0]["winner"] == side
    rows = sheet["rows"]
    assert rows[number - 1]["marker"] is None
    assert rows[number - 1]["score_after"] == "11-0-2", rows[number - 1]
    corrected = taglib.with_winner(taglib.CONFLICT_TAGS, rally=number, side=side)
    expected = taglib.expected_rows(corrected, first_serving_side="A")
    assert taglib.compare_rows(expected, _rows(sheet, tuple(taglib.ROW_FIELDS))) == []


@then(
    parsers.parse("rallies {first:d} to {last:d} are listed as needing her decision, not deleted")
)
def needs_decision(state: dict[str, Any], first: int, last: int) -> None:
    rows = state["book"].sheet()["rows"]
    assert len(rows) == last, "a rally was deleted"
    for row in rows[first - 1 : last]:
        assert row["marker"] == contract.NEEDS_DECISION, row
        assert row["score_after"] is None, row
    ids = {row["rally_id"] for row in rows}
    assert ids == {str(i) for i in state["book"].rally_ids}


@then("game 1 is no longer over")
def game_1_not_over(state: dict[str, Any]) -> None:
    game = state["book"].sheet()["games"][0]
    assert game["winner"] is None, game


@then("the rallies of game 2 are listed as needing her decision, not deleted")
def game_2_needs_decision(state: dict[str, Any]) -> None:
    rows = state["book"].sheet()["rows"]
    assert len(rows) == len(C03_GAME1) + len(C03_GAME2), "a rally was deleted"
    game_2 = [r for r in rows if r["game"] == 2]
    assert len(game_2) == len(C03_GAME2)
    assert all(r["marker"] == contract.NEEDS_DECISION for r in game_2), game_2
    assert all(r["marker"] is None for r in rows if r["game"] == 1)


# ------------------------------------------------------------------ C3-03 (Sprint 3 §7.7)
@given("rallies 12 to 14 need Ivy's decision")
def rallies_12_to_14_need_a_decision(state: dict[str, Any]) -> None:
    conflict_game(state)
    state["book"].correct_winner(11, "A")
    state["book"].start("B")  # game 2 exists, so "move to the next game" has a target
    markers = [r["marker"] for r in state["book"].sheet()["rows"]]
    assert markers[11:] == ["needs_decision"] * 3


def _move(book: Book, number: int) -> Any:
    return book.book.resolve(
        book.rally_ids[number - 1], "move_to_next_game",
        expected_version=book.book.version, ctx=book.ctx,
    )  # fmt: skip


@when("she opens the options of rally 12")
def options_of_rally_12(state: dict[str, Any]) -> None:
    from racket.platform.errors import ValidationFailed

    with pytest.raises(ValidationFailed) as refused:
        _move(state["book"], 12)
    state["refused"] = refused.value


@then('"Move to the next game" is not offered')
def move_not_offered(state: dict[str, Any]) -> None:
    assert state["refused"] is not None
    # positive control: the latest kept rally (14) can be moved, so the refusal is about order
    moved = _move(state["book"], 14)
    assert moved.version > state["book"].book.version


@then("she is told only the latest kept rally can be moved first")
def told_latest_first(state: dict[str, Any]) -> None:
    codes = [(f.field, f.code) for f in state["refused"].fields]
    assert ("decision", "not_last_in_game") in codes, codes


# ------------------------------------------------------------------ C3-03 move back (QA-C303-01)
@given("game 1 is no longer over and rallies 23 to 27 of game 2 need Ivy's decision")
def game_1_reopened(state: dict[str, Any]) -> None:
    two_games(state)
    state["book"].correct_winner(22, "B")
    sheet = state["book"].sheet()
    assert sheet["games"][0]["winner"] is None
    assert [r["marker"] for r in sheet["rows"][22:]] == ["needs_decision"] * 5


def _move_back(book: Book, number: int) -> Any:
    return book.book.resolve(
        book.rally_ids[number - 1], "move_to_previous_game",
        expected_version=book.book.version, ctx=book.ctx,
    )  # fmt: skip


@when("she opens the options of rally 24")
def options_of_rally_24(state: dict[str, Any]) -> None:
    from racket.platform.errors import ValidationFailed

    with pytest.raises(ValidationFailed) as refused:
        _move_back(state["book"], 24)
    state["refused"] = refused.value


@then('"Move back to game 1" is not offered')
def move_back_not_offered(state: dict[str, Any]) -> None:
    assert state["refused"] is not None


@then("she is told only the first rally of game 2 can move back first")
def told_first_first(state: dict[str, Any]) -> None:
    codes = [(f.field, f.code) for f in state["refused"].fields]
    assert ("decision", "not_first_in_game") in codes, codes


@then("rally 23 can be moved back to game 1")
def rally_23_moves_back(state: dict[str, Any]) -> None:
    # positive control: the refusal of rally 24 is about order, not about moving back at all
    moved = _move_back(state["book"], 23)
    assert moved.version > state["book"].book.version
