"""PE-S2-R1-05: a match whose (rules_version, format) pair has no rules preset cannot be scored.

Today only doubles has a preset (singles waits on stretch ST-035, match-aggregate §8 Q3). Without
a preset every tag would be stored unscored and marked "needs your decision" with no resolution,
so ``start_game`` and ``tag`` refuse with 409 ``rules_unavailable`` and nothing is written
(BE-D1-05). Negative first.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from racket.matches.scorebook.domain import (
    CommandContext,
    OutcomeInput,
    RallyTimes,
    RulesUnavailable,
    Scorebook,
)
from racket.platform.errors import CODE_MESSAGES
from racket.sports.pickleball.rules import Side

pytestmark = [pytest.mark.unit, pytest.mark.scoring]

CTX = CommandContext(actor_id=uuid.UUID(int=1), at=datetime(2026, 10, 6, tzinfo=UTC))
WIN_A = {"ending": "winner", "winning_side": "A"}


def _start(book: Scorebook) -> Scorebook:
    return book.start_game(
        first_serving_side=Side.A, ends_switched=False, ready=True,
        expected_version=book.version, ctx=CTX,
    )  # fmt: skip


@pytest.mark.parametrize(
    ("rules_version", "format"),
    [("PROVISIONAL-UNVERIFIED", "singles"), ("NO-SUCH-RULES", "doubles")],
)
def test_a_game_cannot_start_without_a_rules_preset(rules_version: str, format: str) -> None:
    book = Scorebook.new(rules_version=rules_version, format=format)
    with pytest.raises(RulesUnavailable) as exc:
        _start(book)
    assert (exc.value.status, exc.value.code) == (409, "rules_unavailable")
    assert exc.value.code in CODE_MESSAGES  # the FE explains it with a fixed message


def test_a_tag_is_refused_without_a_rules_preset_even_with_a_started_game() -> None:
    """Stored data from before the fix: a singles game already started is not taggable."""
    doubles = _start(Scorebook.new(rules_version="PROVISIONAL-UNVERIFIED", format="doubles"))
    book = Scorebook.new(rules_version="PROVISIONAL-UNVERIFIED", format="singles")
    book = replace(book, games=doubles.games, version=1)
    with pytest.raises(RulesUnavailable):
        book.tag(
            RallyTimes.parse(0, 900),
            OutcomeInput.parse(WIN_A, format="singles"),
            ready=True,
            expected_version=1,
            ctx=CTX,
        )


def test_doubles_with_the_provisional_preset_still_starts() -> None:
    book = _start(Scorebook.new(rules_version="PROVISIONAL-UNVERIFIED", format="doubles"))
    assert [g.number for g in book.games] == [1]
