"""Review round 1 regressions for ``UploadSession`` (R1-01, R1-04, SEC-R1-02; ADR 0011).

* R1-01: a zero-length chunk was recorded as a staged chunk with the same staging key as the
  next real chunk, so the assembled part held those bytes twice.
* R1-04 / SEC-R1-02: a completed upload still planned a "completing" part for a 0-byte chunk.
"""

from __future__ import annotations

import uuid

import pytest

from racket.video_ingest.domain import (
    ObjectKeyPolicy,
    UploadAlreadyComplete,
    UploadSession,
    UploadStatus,
)

KIB = 1024
PART_MIN = 5 * KIB


def session(length: int = 20 * KIB) -> UploadSession:
    return UploadSession.start(
        owner_id=uuid.uuid4(),
        match_id=uuid.uuid4(),
        length=length,
        max_length=10 * 1024 * KIB,
        object_key=ObjectKeyPolicy().original_key(),
        s3_upload_id="mpu-1",
    )


def write(s: UploadSession, offset: int, size: int) -> None:
    plan = s.plan_chunk(offset, size, PART_MIN)
    if plan.is_noop:
        return
    if plan.as_part:
        s.commit_part(plan, etag=f'"etag-{plan.part_number}"')
    else:
        s.commit_staged(plan, staging_key=ObjectKeyPolicy.staging_key(s.id, offset))


def completed() -> UploadSession:
    s = session(8 * KIB)
    write(s, 0, 8 * KIB)
    s.mark_complete(uuid.uuid4())
    return s


# ---------------------------------------------------------------- negative cases first
@pytest.mark.parametrize("size", [0, 1, 4 * KIB])
def test_a_completed_upload_refuses_every_chunk_and_changes_nothing(size: int) -> None:
    s = completed()
    before = (s.offset, list(s.parts), list(s.staged), s.status)

    with pytest.raises(UploadAlreadyComplete):
        s.plan_chunk(s.length, size, PART_MIN)

    assert (s.offset, s.parts, s.staged, s.status) == before


def test_upload_already_complete_maps_to_409_conflict() -> None:
    assert (UploadAlreadyComplete.status, UploadAlreadyComplete.code) == (409, "conflict")


def test_an_upload_at_full_length_refuses_chunks_even_before_it_is_marked_complete() -> None:
    s = session(8 * KIB)
    write(s, 0, 8 * KIB)
    assert s.status is UploadStatus.RECEIVING

    with pytest.raises(UploadAlreadyComplete):
        s.plan_chunk(8 * KIB, 0, PART_MIN)


def test_a_zero_length_plan_cannot_be_committed() -> None:
    s = session()
    plan = s.plan_chunk(0, 0, PART_MIN)

    with pytest.raises(ValueError, match="empty"):
        s.commit_staged(plan, staging_key=ObjectKeyPolicy.staging_key(s.id, 0))
    with pytest.raises(ValueError, match="empty"):
        s.commit_part(plan, etag='"e"')
    assert (s.offset, s.parts, s.staged) == (0, [], [])


def test_a_staging_key_is_never_recorded_twice() -> None:
    s = session()
    write(s, 0, 1 * KIB)
    key = s.staged[0].key
    plan = s.plan_chunk(1 * KIB, 1 * KIB, PART_MIN)

    with pytest.raises(ValueError, match="already staged"):
        s.commit_staged(plan, staging_key=key)
    assert len(s.staged) == 1


# ---------------------------------------------------------------- positive cases
@pytest.mark.parametrize("offset", [0, 3 * KIB])
def test_a_zero_length_chunk_while_receiving_is_a_no_op(offset: int) -> None:
    s = session()
    write(s, 0, offset)

    plan = s.plan_chunk(offset, 0, PART_MIN)

    assert plan.is_noop
    assert (plan.as_part, plan.completes, plan.staged, plan.new_offset) == (
        False, False, (), offset,
    )  # fmt: skip
    assert s.offset == offset


def test_empty_chunk_then_data_stages_each_byte_once() -> None:
    """The R1-01 sequence: PATCH 0 b'' then 2 KiB then the rest."""
    s = session(6 * KIB)

    write(s, 0, 0)
    write(s, 0, 2 * KIB)
    write(s, 2 * KIB, 4 * KIB)

    assert s.staged == []
    assert [p.size for p in s.parts] == [6 * KIB]
    assert s.offset == s.length
