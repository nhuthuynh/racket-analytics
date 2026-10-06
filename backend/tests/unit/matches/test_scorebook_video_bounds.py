"""A rally lies inside the match video (QA-S2-API-02; FR-027, QD-TR-02).

Times are integer ms from the start of the video and ``end_ms`` is exclusive, so a rally may
end exactly at the video's duration but not after it. Negative cases first: a tag and a time
correction that end after the video are ``invalid_rally`` / ``time_after_video`` and change
nothing; then the boundary and the "duration unknown" case are accepted.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from itertools import count

import pytest

from racket.matches.scorebook.domain import (
    CommandContext,
    InvalidRally,
    OutcomeInput,
    RallyTimes,
    Scorebook,
)
from racket.platform.errors import FieldError
from racket.sports.pickleball.rules import Side

pytestmark = [pytest.mark.unit, pytest.mark.scoring]

VIDEO_MS = 60_000  # the 60 s fixture clip
AT = datetime(2026, 10, 6, 12, tzinfo=UTC)


def _ctx() -> CommandContext:
    ids = count(1)
    return CommandContext(actor_id=uuid.UUID(int=5), at=AT, new_id=lambda: uuid.UUID(int=next(ids)))


def _started() -> tuple[Scorebook, CommandContext]:
    ctx = _ctx()
    book = Scorebook.new(rules_version="PROVISIONAL-UNVERIFIED", format="doubles")
    book = book.start_game(
        first_serving_side=Side.A, ends_switched=False, ready=True, expected_version=0, ctx=ctx
    )
    return book, ctx


def _won() -> OutcomeInput:
    return OutcomeInput.parse({"ending": "winner", "winning_side": "A"}, format="doubles")


def _tag(book: Scorebook, ctx: CommandContext, start: int, end: int, video_ms: int | None):
    return book.tag(
        RallyTimes.parse(start, end),
        _won(),
        ready=True,
        expected_version=book.version,
        ctx=ctx,
        video_ms=video_ms,
    )


# ---------------------------------------------------------------- negative first
def test_a_rally_that_starts_after_the_video_ends_is_refused() -> None:
    book, ctx = _started()
    with pytest.raises(InvalidRally) as exc:
        _tag(book, ctx, 872_000, 878_000, VIDEO_MS)  # 14:32 on a 60 s clip
    assert (exc.value.status, exc.value.code) == (422, "invalid_rally")
    assert list(exc.value.fields) == [FieldError("end_ms", "time_after_video")]


def test_a_rally_that_runs_past_the_end_of_the_video_is_refused() -> None:
    book, ctx = _started()
    with pytest.raises(InvalidRally) as exc:
        _tag(book, ctx, 59_000, VIDEO_MS + 1, VIDEO_MS)
    assert list(exc.value.fields) == [FieldError("end_ms", "time_after_video")]


def test_a_time_correction_past_the_end_of_the_video_is_refused() -> None:
    book, ctx = _started()
    book, rally = _tag(book, ctx, 1_000, 2_000, VIDEO_MS)
    with pytest.raises(InvalidRally) as exc:
        book.correct(
            rally.id,
            "end_ms",
            VIDEO_MS + 500,
            expected_version=book.version,
            ctx=ctx,
            video_ms=VIDEO_MS,
        )
    assert list(exc.value.fields) == [FieldError("end_ms", "time_after_video")]


def test_a_start_correction_is_checked_against_the_video_too() -> None:
    book, ctx = _started()
    book, rally = _tag(book, ctx, 58_000, VIDEO_MS, VIDEO_MS)
    moved = book.correct(
        rally.id, "start_ms", 59_000, expected_version=book.version, ctx=ctx, video_ms=VIDEO_MS
    )
    assert moved.version == book.version + 1


# ---------------------------------------------------------------- positive
def test_a_rally_may_end_exactly_at_the_end_of_the_video() -> None:
    book, ctx = _started()
    after, rally = _tag(book, ctx, 59_000, VIDEO_MS, VIDEO_MS)
    assert (after.version, rally.times.end_ms) == (book.version + 1, VIDEO_MS)


def test_without_a_known_duration_no_upper_bound_is_applied() -> None:
    book, ctx = _started()
    after, _ = _tag(book, ctx, 872_000, 878_000, None)
    assert after.version == book.version + 1


def test_the_bound_is_optional_so_existing_callers_keep_working() -> None:
    book, ctx = _started()
    after, _ = book.tag(
        RallyTimes.parse(872_000, 878_000), _won(), ready=True, expected_version=1, ctx=ctx
    )
    assert after.version == 2


def test_check_within_is_a_pure_value_rule() -> None:
    times = RallyTimes.parse(0, VIDEO_MS)
    times.check_within(VIDEO_MS)
    times.check_within(None)
    with pytest.raises(InvalidRally):
        times.check_within(VIDEO_MS - 1)
