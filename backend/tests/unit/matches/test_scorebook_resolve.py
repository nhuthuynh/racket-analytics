"""Resolving a "needs your decision" rally (ST-032 slice 2; FR-053 (a); match-aggregate §4
``resolve``). Provisional: the choices wait on the coach (§8 Q1), so ``needs_verification``.

Negative first: 1. a rally that needs no decision -> refused; 2. an unknown decision -> refused;
3. moving to a game that is not started -> refused; then the two decisions, each audited and
undoable.
"""

from __future__ import annotations

import pytest

from racket.matches.scorebook.domain import GameNotStarted
from racket.platform.errors import ValidationFailed
from tests.unit.matches.test_scorebook_corrections import Book, fresh

pytestmark = [pytest.mark.unit, pytest.mark.scoring, pytest.mark.needs_verification]

CONFLICT = ["A"] * 10 + ["B", "A", "A", "A"]  # taglib.CONFLICT_TAGS: won 11-0 at rally 14


def conflicted() -> Book:
    return fresh(*CONFLICT).correct(11, "winning_side", "A")  # rallies 12-14 need a decision


def resolve(b: Book, n: int, decision: str) -> Book:
    b.b = b.b.resolve(b.ids[n - 1], decision, expected_version=b.v, ctx=b.ctx)
    return b


def codes(exc: pytest.ExceptionInfo[ValidationFailed]) -> list[tuple[str | None, str]]:
    return [(f.field, f.code) for f in exc.value.fields]


def test_a_rally_that_needs_no_decision_cannot_be_resolved() -> None:
    with pytest.raises(ValidationFailed) as exc:
        resolve(conflicted(), 5, "withdraw")
    assert codes(exc) == [("decision", "not_needed")]


@pytest.mark.parametrize("decision", ["keep_in_game", "delete", "", None])
def test_an_unknown_decision_is_refused(decision: str) -> None:
    with pytest.raises(ValidationFailed) as exc:
        resolve(conflicted(), 12, decision)
    assert codes(exc) == [("decision", "decision_invalid")]


def test_moving_to_a_game_that_is_not_started_is_refused() -> None:
    with pytest.raises(GameNotStarted):
        resolve(conflicted(), 12, "move_to_next_game")


def test_withdraw_keeps_the_rally_stored_audited_and_undoable() -> None:
    b = conflicted()
    before = b.bytes()
    resolve(b, 12, "withdraw")
    rows = b.sheet()["rows"]
    assert [r["number"] for r in rows if r["marker"] == "needs_decision"] == [12, 13]
    assert len(b.b.rallies) == 14
    change = b.b.changes[-1]
    assert (change.kind, change.field, change.old_value, change.new_value) == (
        "resolution", "withdrawn", False, True)
    b.undo()
    assert b.bytes() == before


def test_move_to_next_game_scores_the_rallies_in_game_2() -> None:
    b = conflicted().start("B")
    before = b.bytes()
    for n in (12, 13, 14):
        resolve(b, n, "move_to_next_game")
    sheet = b.sheet()
    assert [r["marker"] for r in sheet["rows"][11:]] == [None, None, None]
    assert [r["game"] for r in sheet["rows"][11:]] == [2, 2, 2]
    assert all(r["corrected_by_user"] for r in sheet["rows"][11:])
    for _ in range(3):
        b.undo()
    assert b.bytes() == before
