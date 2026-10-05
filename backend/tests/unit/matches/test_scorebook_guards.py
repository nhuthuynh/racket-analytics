"""The remaining refusals of the scorebook commands and values (ST-026..ST-032), negative cases
the story tests do not reach: a bad match length, an unstated first server, a tag while a
decision is pending, bad withdrawals, stale versions on undo and resolve, malformed outcomes.
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.matches.scorebook.domain import (
    DecisionNeeded,
    InvalidOutcome,
    OutcomeInput,
    RallyNotFound,
    RallyTimes,
    Scorebook,
    StaleMatch,
)
from racket.platform.errors import ValidationFailed
from tests.unit.matches.test_scorebook_corrections import Book, fresh

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("best_of", [0, 2, 5, True])
def test_a_match_is_best_of_1_or_3(best_of: Any) -> None:
    with pytest.raises(ValueError, match="best_of"):
        Scorebook.new(rules_version="PROVISIONAL-UNVERIFIED", format="doubles", best_of=best_of)


def test_the_first_serving_side_must_be_stated() -> None:
    b = Book()
    with pytest.raises(ValueError, match="stated"):
        b.b.start_game(
            first_serving_side="A",
            ends_switched=False,
            ready=True,  # type: ignore[arg-type]
            expected_version=0,
            ctx=b.ctx,
        )


def test_no_tag_while_rallies_wait_for_a_decision() -> None:
    b = fresh(*(["A"] * 10 + ["B", "A", "A", "A"])).correct(11, "winning_side", "A")
    outcome = OutcomeInput.parse({"ending": "winner", "winning_side": "A"}, format="doubles")
    with pytest.raises(DecisionNeeded) as exc:
        b.b.tag(
            RallyTimes.parse(90_000, 91_000), outcome, ready=True, expected_version=b.v, ctx=b.ctx
        )
    assert (exc.value.status, exc.value.code) == (409, "decision_needed")


@pytest.mark.parametrize("value", [False, "yes", 1])
def test_withdrawn_takes_only_true(value: Any) -> None:
    with pytest.raises(ValidationFailed):
        fresh("A").correct(1, "withdrawn", value)


def test_a_withdrawn_rally_cannot_be_withdrawn_again_or_corrected() -> None:
    b = fresh("A", "B").correct(2, "withdrawn", True)
    with pytest.raises(ValidationFailed):
        b.correct(2, "withdrawn", True)
    with pytest.raises(RallyNotFound):
        b.correct(2, "winning_side", "A")


def test_undo_and_resolve_check_the_version_first() -> None:
    b = fresh("A")
    with pytest.raises(StaleMatch):
        b.b.undo(expected_version=b.v + 1, ctx=b.ctx)
    with pytest.raises(StaleMatch):
        b.b.resolve(b.ids[0], "withdraw", expected_version=b.v - 1, ctx=b.ctx)


@pytest.mark.parametrize("body", [None, [], "winner"])
def test_an_outcome_that_is_not_an_object_is_refused(body: Any) -> None:
    with pytest.raises(InvalidOutcome) as exc:
        OutcomeInput.parse(body, format="doubles")
    assert [(f.field, f.code) for f in exc.value.fields] == [(None, "invalid")]


@pytest.mark.parametrize("side", ["C", "a", 1, ""])
def test_an_unknown_winning_side_is_refused(side: Any) -> None:
    with pytest.raises(InvalidOutcome) as exc:
        OutcomeInput.parse({"ending": "winner", "winning_side": side}, format="doubles")
    assert ("winning_side", "side_invalid") in [(f.field, f.code) for f in exc.value.fields]
