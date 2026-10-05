"""``UploadPolicy`` (ST-018; FR-023; api-sprint-01 §6.3, §6.5, §6.6; threat model T-UV-1..3).

sprint-01 §5 order: 1. ``Upload-Length`` > cap -> rejected before storage; 2. non-video magic
bytes -> not a video; 3. MP4/MOV with H.264/HEVC accepted; 4. duration > cap (from the probe)
-> rejected. Boundaries cap - 1, cap, cap + 1 for every cap (T-UV-3). Content decides, never
the file name or ``Content-Type`` (T-UV-1).
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.video_ingest.domain import MediaFacts, Rejection, UploadPolicy

CAP_BYTES = 10_000_000_000
CAP_MS = 9_000_000
CAP_PIXELS = 3840 * 2160
POLICY = UploadPolicy(max_bytes=CAP_BYTES, max_duration_ms=CAP_MS, max_frame_pixels=CAP_PIXELS)
PHONE = MediaFacts(
    container="mov,mp4,m4a,3gp,3g2,mj2", video_codec="h264", duration_ms=60_000, fps=60.0,
    vfr=False, width=1920, height=1080, has_audio=True,
)  # fmt: skip
MP4_HEAD = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00"
PDF_HEAD = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
ELF_HEAD = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8


# ---------------------------------------------------------------- 1. declared size
@pytest.mark.parametrize(
    ("length", "expected"),
    [(CAP_BYTES - 1, None), (CAP_BYTES, None), (CAP_BYTES + 1, Rejection.TOO_LARGE),
     (12 * 1000**3, Rejection.TOO_LARGE)],
)  # fmt: skip
def test_the_declared_length_is_checked_against_the_cap(
    length: int, expected: Rejection | None
) -> None:
    assert POLICY.check_declared_length(length) == expected


# ---------------------------------------------------------------- 2. magic bytes
@pytest.mark.parametrize("head", [PDF_HEAD, ELF_HEAD, b"", b"\x00" * 12, b"GIF89a" + b"\x00" * 6])
def test_content_that_is_not_mp4_or_mov_is_not_a_video(head: bytes) -> None:
    assert UploadPolicy.sniff(head, length=1_000_000) == Rejection.NOT_A_VIDEO


@pytest.mark.parametrize("atom", [b"ftyp", b"moov", b"mdat", b"wide", b"free", b"skip"])
def test_mp4_and_quicktime_top_level_atoms_pass(atom: bytes) -> None:
    assert UploadPolicy.sniff(b"\x00\x00\x00\x08" + atom + b"\x00" * 8, length=10_000) is None


def test_a_first_chunk_too_short_to_show_the_atom_is_not_a_video() -> None:
    assert UploadPolicy.sniff(MP4_HEAD[:7], length=10_000) == Rejection.NOT_A_VIDEO


def test_a_tiny_file_shorter_than_an_atom_header_is_not_a_video() -> None:
    assert UploadPolicy.sniff(b"\x00\x00\x00\x08ftyp"[:6], length=6) == Rejection.NOT_A_VIDEO


@given(st.binary(max_size=64), st.integers(min_value=1, max_value=10**12))
def test_sniff_never_raises(head: bytes, length: int) -> None:
    assert UploadPolicy.sniff(head, length=length) in (None, Rejection.NOT_A_VIDEO)


# ---------------------------------------------------------------- 3. container and codec
@pytest.mark.parametrize("codec", ["h264", "hevc"])
@pytest.mark.parametrize("container", ["mov,mp4,m4a,3gp,3g2,mj2", "mp4", "mov"])
def test_mp4_or_mov_with_h264_or_hevc_is_accepted(container: str, codec: str) -> None:
    assert POLICY.check(replace(PHONE, container=container, video_codec=codec)) is None


@pytest.mark.parametrize(
    "changes",
    [{"video_codec": "vp9"}, {"video_codec": "prores"}, {"container": "matroska,webm"},
     {"container": "avi"}, {"width": 7680, "height": 4320}],
)  # fmt: skip
def test_other_containers_codecs_or_huge_frames_are_unsupported(changes: dict[str, object]) -> None:
    assert POLICY.check(replace(PHONE, **changes)) == Rejection.UNSUPPORTED_VIDEO  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("cap", "expected"),
    [(1920 * 1080 - 1, Rejection.UNSUPPORTED_VIDEO), (1920 * 1080, None), (1920 * 1080 + 1, None)],
)
def test_frame_pixel_cap_boundaries(cap: int, expected: Rejection | None) -> None:
    assert replace(POLICY, max_frame_pixels=cap).check(PHONE) == expected


# ---------------------------------------------------------------- 4. duration from the probe
@pytest.mark.parametrize(
    ("duration_ms", "expected"),
    [(CAP_MS - 1, None), (CAP_MS, None), (CAP_MS + 1, Rejection.TOO_LONG),
     (4 * 3600 * 1000, Rejection.TOO_LONG)],
)  # fmt: skip
def test_duration_cap_boundaries(duration_ms: int, expected: Rejection | None) -> None:
    assert POLICY.check(replace(PHONE, duration_ms=duration_ms)) == expected


def test_an_unsupported_video_is_reported_before_its_length() -> None:
    facts = replace(PHONE, video_codec="vp9", duration_ms=CAP_MS + 1)
    assert POLICY.check(facts) == Rejection.UNSUPPORTED_VIDEO


def test_rejection_codes_are_the_contract_codes() -> None:
    assert {r.value for r in Rejection} == {"not_a_video", "too_large", "too_long",
                                            "unsupported_video"}  # fmt: skip
