"""UploadSession and ObjectKeyPolicy (ST-008; sprint-00 §5 TDD plan, in order; ADR 0011)."""

from __future__ import annotations

import re
import uuid

import pytest

from racket.video_ingest.domain import (
    ChunkBeyondLength,
    InvalidUploadLength,
    ObjectKeyPolicy,
    OffsetMismatch,
    UploadIncomplete,
    UploadSession,
    UploadStatus,
)

KIB = 1024
PART_MIN = 5 * KIB  # small parts keep the arithmetic readable; production uses 5 MiB


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
    if plan.as_part:
        s.commit_part(plan, etag=f'"etag-{plan.part_number}"')
    else:
        s.commit_staged(plan, staging_key=ObjectKeyPolicy.staging_key(s.id, offset))


# ---------------------------------------------------------------- UploadSession
# 1. PATCH with offset != current offset -> OffsetMismatch, state unchanged
@pytest.mark.parametrize("wrong", [0, 3 * KIB, 4 * KIB + 1, 20 * KIB])
def test_wrong_offset_is_a_mismatch_and_changes_nothing(wrong: int) -> None:
    s = session()
    write(s, 0, 4 * KIB)

    with pytest.raises(OffsetMismatch):
        s.plan_chunk(wrong, KIB, PART_MIN)

    assert s.offset == 4 * KIB
    assert len(s.staged) == 1


# 2. PATCH beyond Upload-Length -> error
def test_chunk_past_the_declared_length_is_refused() -> None:
    s = session(length=10 * KIB)

    with pytest.raises(ChunkBeyondLength):
        s.plan_chunk(0, 10 * KIB + 1, PART_MIN)

    assert s.offset == 0


def test_offset_mismatch_wins_over_overflow() -> None:
    """ADR 0011 step 1: the 409 check runs before the length check."""
    s = session(length=10 * KIB)

    with pytest.raises(OffsetMismatch):
        s.plan_chunk(KIB, 20 * KIB, PART_MIN)


# 3. PATCH at the right offset advances it
def test_chunk_at_the_right_offset_advances_the_offset() -> None:
    s = session()

    write(s, 0, 2 * KIB)
    write(s, 2 * KIB, 2 * KIB)

    assert s.offset == 4 * KIB


def test_small_chunks_are_staged_until_a_part_is_big_enough() -> None:
    s = session()
    write(s, 0, 2 * KIB)
    write(s, 2 * KIB, 2 * KIB)

    plan = s.plan_chunk(4 * KIB, 2 * KIB, PART_MIN)

    assert plan.as_part
    assert plan.part_number == 1
    assert [st.offset for st in plan.staged] == [0, 2 * KIB]
    s.commit_part(plan, etag='"e1"')
    assert s.staged == []
    assert [(p.number, p.size) for p in s.parts] == [(1, 6 * KIB)]


def test_final_chunk_is_always_a_part_even_when_small() -> None:
    s = session(length=3 * KIB)
    write(s, 0, KIB)

    plan = s.plan_chunk(KIB, 2 * KIB, PART_MIN)

    assert plan.as_part
    assert plan.completes


# 4. is_complete only when offset equals length
def test_is_complete_only_when_offset_equals_length() -> None:
    s = session(length=8 * KIB)
    write(s, 0, 6 * KIB)
    assert not s.is_complete

    write(s, 6 * KIB, 2 * KIB)

    assert s.is_complete
    s.mark_complete()
    assert s.status is UploadStatus.COMPLETE


def test_mark_complete_before_the_last_byte_fails() -> None:
    s = session(length=8 * KIB)
    write(s, 0, 6 * KIB)

    with pytest.raises(UploadIncomplete):
        s.mark_complete()


@pytest.mark.parametrize("length", [0, -1, 10 * 1024 * KIB + 1])
def test_declared_length_must_be_within_limits(length: int) -> None:
    with pytest.raises(InvalidUploadLength):
        session(length=length)


# ---------------------------------------------------------------- ObjectKeyPolicy
# 1. user filename never appears in the key
def test_original_key_is_random_and_takes_no_user_input() -> None:
    key = ObjectKeyPolicy().original_key()

    assert re.fullmatch(r"originals/[0-9a-f]{32}", key)
    with pytest.raises(TypeError):
        ObjectKeyPolicy().original_key("../../etc/passwd.mp4")  # type: ignore[call-arg]


# 2. keys are unique per call
def test_original_keys_are_unique_per_call() -> None:
    policy = ObjectKeyPolicy()

    keys = {policy.original_key() for _ in range(1000)}

    assert len(keys) == 1000


def test_staging_key_is_derived_from_server_ids_only() -> None:
    upload_id = uuid.uuid4()

    assert ObjectKeyPolicy.staging_key(upload_id, 42) == f"staging/{upload_id.hex}/{42:020d}"
