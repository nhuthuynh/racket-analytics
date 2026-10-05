"""tus checksum and expiration extensions on ``UploadSession`` (ST-017; api-sprint-01 §6.3-§6.5;
threat model T-UV-5/6/7). sprint-01 §5 order: 1. checksum mismatch -> chunk rejected, offset
unchanged; 2. expired session refuses PATCH; 3. ``Upload-Expires`` is set at creation.
Parsers of untrusted headers get property tests (retro 0 L4, testing-strategy rule 9).
"""

from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.platform.errors import AppError, BadRequest
from racket.video_ingest.domain import (
    ChecksumInvalid,
    ChecksumMismatch,
    ExpiryPolicy,
    ObjectKeyPolicy,
    UploadChecksum,
    UploadExpired,
    UploadFile,
    UploadSession,
    UploadStatus,
)

KIB = 1024
T0 = datetime(2026, 10, 5, 9, 0, tzinfo=UTC)
POLICY = ExpiryPolicy(idle=timedelta(hours=24), max_age=timedelta(hours=72))
DATA = bytes(range(256)) * 64  # 16 KiB


def b64(digest: bytes) -> str:
    return base64.b64encode(digest).decode()


def header(data: bytes, algorithm: str = "sha256") -> str:
    return f"{algorithm} {b64(hashlib.new(algorithm, data).digest())}"


def session(*, head: str | None = None, length: int = len(DATA)) -> UploadSession:
    return UploadSession.start(
        owner_id=uuid.uuid4(),
        match_id=uuid.uuid4(),
        length=length,
        max_length=10 * 1024 * KIB,
        object_key=ObjectKeyPolicy().original_key(),
        s3_upload_id="mpu-1",
        now=T0,
        expiry=POLICY,
        file=UploadFile(name="Sat doubles.mp4", last_modified_ms=1, head_sha256=head),
    )


# ---------------------------------------------------------------- 1. checksum mismatch
def test_a_chunk_that_does_not_match_its_checksum_is_refused() -> None:
    checksum = UploadChecksum.parse(header(DATA[:KIB]))
    damaged = bytes([DATA[0] ^ 0xFF]) + DATA[1:KIB]
    with pytest.raises(ChecksumMismatch) as exc:
        checksum.verify(damaged)
    assert (exc.value.status, exc.value.code) == (460, "checksum_mismatch")


@pytest.mark.parametrize("algorithm", ["sha256", "sha1"])
def test_a_matching_checksum_passes(algorithm: str) -> None:
    UploadChecksum.parse(header(DATA, algorithm)).verify(DATA)


@pytest.mark.parametrize(
    "raw",
    ["md5 AAAA", "sha256", "sha256 !!!notbase64", "sha256  ", "", " sha256 " + "A" * 44,
     "SHA256 " + b64(hashlib.sha256(b"").digest()),  # algorithm names are lower case (tus)
     "sha256 " + b64(b"short"), "sha1 " + b64(hashlib.sha256(b"").digest())],
)  # fmt: skip
def test_a_malformed_or_unsupported_checksum_header_is_a_400(raw: str) -> None:
    with pytest.raises(ChecksumInvalid) as exc:
        UploadChecksum.parse(raw)
    assert isinstance(exc.value, BadRequest)
    assert exc.value.code == "checksum_invalid"


@given(st.text(max_size=120))
def test_the_checksum_parser_only_ever_refuses_with_checksum_invalid(raw: str) -> None:
    try:
        parsed = UploadChecksum.parse(raw)
    except ChecksumInvalid:
        return
    assert parsed.algorithm in ("sha256", "sha1")
    assert len(parsed.digest) == {"sha256": 32, "sha1": 20}[parsed.algorithm]


# ---------------------------------------------------------------- T-UV-6: same file on resume
def test_the_first_chunk_of_another_file_is_refused_when_a_head_hash_was_given() -> None:
    s = session(head=hashlib.sha256(DATA).hexdigest())
    with pytest.raises(ChecksumMismatch):
        s.verify_head(bytes(reversed(DATA)))
    s.verify_head(DATA)  # positive control


def test_a_first_chunk_shorter_than_the_head_range_cannot_prove_it_is_the_same_file() -> None:
    s = session(head=hashlib.sha256(DATA).hexdigest())
    with pytest.raises(ChecksumMismatch):
        s.verify_head(DATA[:KIB])


def test_no_head_hash_means_no_head_check() -> None:
    session(head=None).verify_head(b"anything")


# ---------------------------------------------------------------- 2. expired session
def test_an_expired_session_refuses_and_is_marked_expired() -> None:
    s = session()
    with pytest.raises(UploadExpired) as exc:
        s.ensure_open(now=T0 + timedelta(hours=24))
    assert (exc.value.status, exc.value.code) == (410, "upload_expired")
    assert s.status is UploadStatus.EXPIRED
    assert s.file is None  # the stored file name goes with the expiry (T-UV-9)


def test_a_session_inside_its_expiry_is_open() -> None:
    s = session()
    s.ensure_open(now=T0 + timedelta(hours=23, minutes=59))
    assert s.status is UploadStatus.RECEIVING


# ---------------------------------------------------------------- 3. Upload-Expires at creation
def test_upload_expires_is_set_at_creation() -> None:
    assert session().expires_at == T0 + timedelta(hours=24)


def test_each_accepted_chunk_slides_the_expiry_up_to_the_cap() -> None:
    s = session()
    s.touch(now=T0 + timedelta(hours=10), expiry=POLICY)
    assert s.expires_at == T0 + timedelta(hours=34)
    s.touch(now=T0 + timedelta(hours=60), expiry=POLICY)
    assert s.expires_at == T0 + timedelta(hours=72)  # capped at 72 h after creation


def test_the_expiry_policy_refuses_a_cap_shorter_than_the_idle_time() -> None:
    with pytest.raises(ValueError, match="max_age"):
        ExpiryPolicy(idle=timedelta(hours=24), max_age=timedelta(hours=1))


def test_completing_drops_the_file_name() -> None:
    s = session()
    plan = s.plan_chunk(0, len(DATA), 5 * KIB)
    s.commit_part(plan, etag='"e"')
    s.mark_complete()
    assert s.file is None


# ---------------------------------------------------------------- Upload-Metadata (§6.3 row 6)
def meta(**pairs: str) -> str:
    return ",".join(f"{k} {base64.b64encode(v.encode()).decode()}" for k, v in pairs.items())


def test_metadata_reads_name_last_modified_and_head_hash_only() -> None:
    head = "a" * 64
    raw = meta(
        filename="Sat doubles.mp4",
        last_modified="1759480000000",
        head_sha256=head,
        filetype="video/mp4",
    )
    expected = UploadFile(name="Sat doubles.mp4", last_modified_ms=1759480000000, head_sha256=head)
    assert UploadFile.from_metadata(raw) == expected


def test_metadata_name_loses_control_characters_and_is_cut_to_255_bytes() -> None:
    parsed = UploadFile.from_metadata(meta(filename="a\x00b\nc" + "é" * 200))
    assert parsed.name is not None
    assert parsed.name.startswith("abc")
    assert len(parsed.name.encode()) <= 255
    assert parsed.name.encode().decode() == parsed.name  # never a split UTF-8 sequence


@pytest.mark.parametrize(
    "pairs",
    [{"head_sha256": "A" * 64}, {"head_sha256": "a" * 63}, {"head_sha256": "g" * 64},
     {"last_modified": "-1"}, {"last_modified": "1.5"}, {"last_modified": "²"}],
)  # fmt: skip
def test_malformed_head_hash_or_last_modified_is_a_400(pairs: dict[str, str]) -> None:
    with pytest.raises(BadRequest):
        UploadFile.from_metadata(meta(**pairs))


def test_no_metadata_is_an_empty_file_record() -> None:
    assert UploadFile.from_metadata(None) == UploadFile(None, None, None)


@given(st.text(max_size=200))
def test_the_metadata_parser_refuses_only_with_400(raw: str) -> None:
    status = 200
    try:
        UploadFile.from_metadata(raw)
    except AppError as exc:
        status = exc.status
    assert status in (200, 400)
