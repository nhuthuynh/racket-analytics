"""``Match.tag_rally`` and ``start_game`` on the scorebook (ST-026/ST-027; match-aggregate §3-§4).

sprint-02 §5 TDD order, negative first: 1. a tag on a match that is over -> ``MatchOver``;
2. a tag on a match whose video is not received -> refused (NFR-060, I1); 3. a tag appends a
rally and the projection shows the new score. Plus the optimistic lock (IT-02-04 at the API).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from itertools import count

import pytest

from racket.matches.scorebook.domain import (
    CommandContext,
    GameIsOver,
    GameNotOver,
    GameNotStarted,
    InvalidRally,
    MatchIsOver,
    MatchNotReady,
    OutcomeInput,
    RallyTimes,
    Scorebook,
    StaleMatch,
    project,
)
from racket.sports.pickleball.rules import Side

pytestmark = [pytest.mark.unit, pytest.mark.scoring]

AT = datetime(2026, 10, 5, 12, tzinfo=UTC)
ACTOR = uuid.UUID(int=7)


def ctx() -> CommandContext:
    ids = count(1)
    return CommandContext(actor_id=ACTOR, at=AT, new_id=lambda: uuid.UUID(int=next(ids)))


def won(side: str, ending: str = "winner") -> OutcomeInput:
    return OutcomeInput.parse({"ending": ending, "winning_side": side}, format="doubles")


class Tagger:
    """Drives a scorebook the way the API does: each command sends the last version."""

    def __init__(self, best_of: int = 3, ready: bool = True) -> None:
        self.book = Scorebook.new(rules_version="PROVISIONAL-UNVERIFIED", format="doubles",
                                  best_of=best_of)  # fmt: skip
        self.ready, self.ctx, self.clock = ready, ctx(), 0

    def start(self, first: str = "A") -> None:
        self.book = self.book.start_game(
            first_serving_side=Side(first), ends_switched=False, ready=self.ready,
            expected_version=self.book.version, ctx=self.ctx,
        )  # fmt: skip

    def tag(self, outcome: OutcomeInput) -> uuid.UUID:
        times = RallyTimes.parse(self.clock, self.clock + 900)
        self.clock += 1_000
        self.book, rally = self.book.tag(
            times, outcome, ready=self.ready, expected_version=self.book.version, ctx=self.ctx
        )
        return rally.id

    def win_game(self, side: str) -> None:
        self.start(side)
        while project(self.book)["games"][-1]["winner"] is None:
            self.tag(won(side))


# ---------------------------------------------------------------- 1. match over
def test_a_tag_after_the_match_is_decided_is_match_over() -> None:
    t = Tagger(best_of=1)
    t.win_game("A")
    with pytest.raises(MatchIsOver) as exc:
        t.tag(won("B"))
    assert (exc.value.status, exc.value.code) == (409, "match_over")


def test_a_tag_on_a_finished_game_is_game_over_until_the_next_game_starts() -> None:
    t = Tagger(best_of=3)
    t.win_game("A")
    with pytest.raises(GameIsOver) as exc:
        t.tag(won("B"))
    assert (exc.value.status, exc.value.code) == (409, "game_over")
    t.start("B")
    t.tag(won("B"))


def test_no_game_starts_after_the_match_is_decided() -> None:
    t = Tagger(best_of=3)
    t.win_game("A")
    t.win_game("A")
    with pytest.raises(MatchIsOver):
        t.start("B")


def test_the_next_game_starts_only_after_the_current_one_is_over() -> None:
    t = Tagger()
    t.start()
    t.tag(won("A"))
    with pytest.raises(GameNotOver) as exc:
        t.start("B")
    assert exc.value.code == "game_not_over"


# ---------------------------------------------------------------- 2. video not received
def test_a_tag_before_the_video_is_received_is_refused_and_nothing_changes() -> None:
    t = Tagger(ready=False)
    with pytest.raises(MatchNotReady) as exc:
        t.tag(won("A"))
    assert (exc.value.status, exc.value.code) == (409, "match_not_ready")
    with pytest.raises(MatchNotReady):
        t.start()
    assert (t.book.version, t.book.rallies, t.book.games) == (0, (), ())


def test_a_tag_before_any_game_is_game_not_started() -> None:
    with pytest.raises(GameNotStarted) as exc:
        Tagger().tag(won("A"))
    assert (exc.value.status, exc.value.code) == (409, "game_not_started")


# ---------------------------------------------------------------- stale version (IT-02-04)
def test_a_command_with_an_older_version_is_stale_and_changes_nothing() -> None:
    t = Tagger()
    t.start()
    before = t.book
    with pytest.raises(StaleMatch) as exc:
        t.book.tag(RallyTimes.parse(0, 10), won("A"), ready=True,
                   expected_version=t.book.version - 1, ctx=t.ctx)  # fmt: skip
    assert (exc.value.status, exc.value.code) == (409, "stale_match")
    assert t.book is before


def test_a_rally_overlapping_the_last_one_is_refused() -> None:
    t = Tagger()
    t.start()
    t.tag(won("A"))
    with pytest.raises(InvalidRally):
        t.book.tag(RallyTimes.parse(500, 1_500), won("A"), ready=True,
                   expected_version=t.book.version, ctx=t.ctx)  # fmt: skip


# ---------------------------------------------------------------- 3. a tag appends a rally
def test_a_tag_appends_a_rally_and_the_projection_shows_the_new_score() -> None:
    t = Tagger()
    t.start("A")
    assert t.book.version == 1
    rally_id = t.tag(won("A"))
    assert t.book.version == 2
    (row,) = project(t.book)["rows"]
    assert row["rally_id"] == str(rally_id)
    assert (row["number"], row["score_before"], row["score_after"]) == (1, "0-0-2", "1-0-2")
    assert (row["serving_side"], row["marker"]) == ("A", None)


def test_each_command_bumps_the_version_by_one_and_records_who_and_when() -> None:
    t = Tagger()
    t.start()
    t.tag(won("B"))
    t.tag(won("A"))
    assert t.book.version == 3
    started = t.book.changes[0]
    assert (started.kind, started.actor_id, started.at, started.version) == (
        "game_started", ACTOR, AT, 1)  # fmt: skip
    assert [r.created_version for r in t.book.rallies] == [2, 3]
