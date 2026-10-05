"""``Match.reject_video`` and ``clear_rejection`` (ST-018; api-sprint-01 §5.2 ``rejection``,
§6.6): a refused file leaves the match with "No video yet" and the reason."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from racket.matches.domain import InvalidMatch, Match, MatchStatus, OwnerId

AT = datetime(2026, 10, 5, 9, 0, tzinfo=UTC)


def a_match() -> Match:
    return Match.create(owner_id=OwnerId.new(), title="Sat doubles", format="doubles")


def test_an_unknown_rejection_code_is_refused() -> None:
    with pytest.raises(InvalidMatch):
        a_match().reject_video("virus", at=AT)


def test_a_rejected_video_returns_the_match_to_awaiting_upload() -> None:
    match = a_match()
    match.mark_uploaded(uuid.uuid4())
    match.reject_video("too_long", at=AT)
    assert match.status is MatchStatus.AWAITING_UPLOAD
    assert match.media_asset_id is None
    assert (match.rejection_code, match.rejected_at) == ("too_long", AT)


def test_a_new_upload_clears_the_last_rejection_and_the_match_can_take_a_video_again() -> None:
    match = a_match()
    match.reject_video("not_a_video", at=AT)
    match.clear_rejection()
    assert (match.rejection_code, match.rejected_at) == (None, None)
    match.mark_uploaded(uuid.uuid4())
    assert match.status is MatchStatus.VIDEO_RECEIVED
