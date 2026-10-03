"""MatchId, OwnerId and the minimal Match aggregate (ST-006; sprint-00 §5 TDD plan, in order)."""

from __future__ import annotations

import uuid

import pytest

from racket.matches.domain import (
    InvalidId,
    InvalidMatch,
    Match,
    MatchAlreadyUploaded,
    MatchFormat,
    MatchId,
    MatchStatus,
    OwnerId,
)
from tests.support.builders import a_match, an_owner


# ---------------------------------------------------------------- MatchId, OwnerId
# 1. non-UUID input rejected
@pytest.mark.parametrize("raw", ["", "42", "not-a-uuid", "../../etc/passwd", "0" * 33])
@pytest.mark.parametrize("id_type", [MatchId, OwnerId])
def test_non_uuid_input_is_rejected(id_type: type[MatchId] | type[OwnerId], raw: str) -> None:
    with pytest.raises(InvalidId):
        id_type(raw)


# 2. generated IDs are UUIDv4
def test_generated_ids_are_uuid4_and_distinct() -> None:
    first, second = MatchId.new(), MatchId.new()

    assert first.value.version == 4
    assert first != second


def test_ids_compare_by_value_and_render_canonically() -> None:
    raw = uuid.uuid4()

    assert MatchId(str(raw).upper()) == MatchId(raw)
    assert str(MatchId(raw.hex)) == str(raw)
    assert MatchId(raw) != OwnerId(raw)  # type: ignore[comparison-overlap]


# ---------------------------------------------------------------- Match
# 1. creating without an owner fails
def test_creating_without_an_owner_fails() -> None:
    with pytest.raises(InvalidMatch):
        Match.create(owner_id=None, title="Skeleton test", format="doubles")  # type: ignore[arg-type]


# 2. unknown format fails
@pytest.mark.parametrize("fmt", ["triples", "", "DOUBLES "])
def test_unknown_format_fails(fmt: str) -> None:
    with pytest.raises(InvalidMatch):
        a_match().with_format(fmt).build()


@pytest.mark.parametrize("title", ["", "   ", "x" * 121])
def test_title_must_have_1_to_120_characters(title: str) -> None:
    with pytest.raises(InvalidMatch):
        a_match().titled(title).build()


def test_title_is_trimmed() -> None:
    assert a_match().titled("  Skeleton test  ").build().title == "Skeleton test"


# 3. a new match has status awaiting_upload
def test_new_match_awaits_upload() -> None:
    match = a_match().with_format("singles").build()

    assert match.status is MatchStatus.AWAITING_UPLOAD
    assert match.format is MatchFormat.SINGLES
    assert match.media_asset_id is None
    assert match.id.value.version == 4


# 4. mark_uploaded(media_id) twice fails
def test_mark_uploaded_twice_fails() -> None:
    match = a_match().build()
    media_id = uuid.uuid4()
    match.mark_uploaded(media_id)

    with pytest.raises(MatchAlreadyUploaded):
        match.mark_uploaded(uuid.uuid4())

    assert match.status is MatchStatus.VIDEO_RECEIVED
    assert match.media_asset_id == media_id


# 5. can_be_read_by(other_owner) is false
def test_only_the_owner_can_read_the_match() -> None:
    ivy = an_owner()
    match = a_match().owned_by(ivy).build()

    assert match.can_be_read_by(ivy.build()) is True
    assert match.can_be_read_by(an_owner().named("carlos").build()) is False
