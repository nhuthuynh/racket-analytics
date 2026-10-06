"""SEC-S2-R1-01 (ASVS 5.0 2.4.1 anti-automation; AQS/SEC-10): a match's scorebook has a cap on
stored rallies and on audit rows, so one account cannot grow ``match_rallies`` or the
append-only ``match_corrections`` without bound, nor make every command's replay cost grow
without bound. The caps come in through ``CommandContext.limits`` (settings in the service).

Past a cap the command is 422 ``scorebook_full`` with ``{"field": null, "code":
"too_many_rallies" | "too_many_changes"}`` and returns nothing new. Negative first.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from itertools import count

import pytest

from racket.matches.scorebook.domain import (
    CommandContext,
    Limits,
    OutcomeInput,
    RallyTimes,
    Scorebook,
    ScorebookFull,
)
from racket.platform.errors import CODE_MESSAGES
from racket.sports.pickleball.rules import Side

pytestmark = [pytest.mark.unit, pytest.mark.scoring]

AT = datetime(2026, 10, 6, tzinfo=UTC)
REPLAY = OutcomeInput.parse({"ending": "replay"}, format="doubles")


def ctx(*, rallies: int = 500, changes: int = 2000) -> CommandContext:
    ids = count(1)
    return CommandContext(
        actor_id=uuid.UUID(int=7),
        at=AT,
        new_id=lambda: uuid.UUID(int=next(ids)),
        limits=Limits(max_rallies=rallies, max_changes=changes),
    )


def started(c: CommandContext) -> Scorebook:
    book = Scorebook.new(rules_version="PROVISIONAL-UNVERIFIED", format="doubles")
    return book.start_game(
        first_serving_side=Side.A, ends_switched=False, ready=True, expected_version=0, ctx=c
    )


def tag(book: Scorebook, c: CommandContext, n: int) -> Scorebook:
    after, _ = book.tag(
        RallyTimes.parse(n * 1000, n * 1000 + 900),
        REPLAY,  # replays never end the game, so the cap is the only refusal
        ready=True,
        expected_version=book.version,
        ctx=c,
    )
    return after


def test_a_tag_past_the_rally_cap_is_refused_and_withdrawn_rallies_count() -> None:
    c = ctx(rallies=3)
    book = started(c)
    for n in range(3):
        book = tag(book, c, n)
    book = book.undo(expected_version=book.version, ctx=c)  # withdrawn, still stored
    with pytest.raises(ScorebookFull) as exc:
        tag(book, c, 10)
    assert (exc.value.status, exc.value.code) == (422, "scorebook_full")
    assert [(f.field, f.code) for f in exc.value.fields] == [(None, "too_many_rallies")]
    assert exc.value.code in CODE_MESSAGES


def test_a_change_past_the_change_cap_is_refused_for_every_audited_command() -> None:
    c = ctx(changes=2)  # the game start + one correction
    book = tag(started(c), c, 0)
    rally = book.rallies[0].id
    book = book.correct(rally, "start_ms", 100, expected_version=book.version, ctx=c)
    for command in (
        lambda b: b.correct(rally, "start_ms", 200, expected_version=b.version, ctx=c),
        lambda b: b.correct(rally, "withdrawn", True, expected_version=b.version, ctx=c),
        lambda b: b.undo(expected_version=b.version, ctx=c),
    ):
        with pytest.raises(ScorebookFull) as exc:
            command(book)
        assert [(f.field, f.code) for f in exc.value.fields] == [(None, "too_many_changes")]


def test_under_the_caps_commands_still_work() -> None:
    c = ctx(rallies=2, changes=2)
    book = tag(tag(started(c), c, 0), c, 1)
    book = book.correct(book.rallies[0].id, "start_ms", 100, expected_version=book.version, ctx=c)
    assert (len(book.rallies), len(book.changes)) == (2, 2)
