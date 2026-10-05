"""``UploadPolicy``: which files become match videos (ST-018; FR-023; api-sprint-01 §6.3, §6.5,
§6.6; threat model T-UV-1..T-UV-3). Pure Python.

Content decides, never the file name or ``Content-Type``: the first bytes must be an MP4 or
QuickTime top-level atom, and after the probe the container, codec, frame size and duration
must be within the caps. The caps are configuration (provisional 10 GB / 150 min until the
ST-025 measurement, K12).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from racket.video_ingest.domain.media_facts import MediaFacts

# Bytes 4-7 of an MP4/MOV file: the type of its first top-level atom (ISO BMFF / QuickTime).
TOP_LEVEL_ATOMS = frozenset({b"ftyp", b"moov", b"mdat", b"wide", b"free", b"skip"})
SNIFF_BYTES = 12


class Rejection(StrEnum):
    """The ``rejection.code`` values of the match read model (api-sprint-01 §5.2)."""

    NOT_A_VIDEO = "not_a_video"
    TOO_LARGE = "too_large"
    TOO_LONG = "too_long"
    UNSUPPORTED_VIDEO = "unsupported_video"


@dataclass(frozen=True)
class UploadPolicy:
    max_bytes: int
    max_duration_ms: int
    max_frame_pixels: int = 8_294_400
    containers: tuple[str, ...] = ("mp4", "mov")
    video_codecs: tuple[str, ...] = ("h264", "hevc")

    def check_declared_length(self, length: int) -> Rejection | None:
        """Before any byte is stored (NFR-053, T-UV-2)."""
        return Rejection.TOO_LARGE if length > self.max_bytes else None

    @staticmethod
    def sniff(first_bytes: bytes, *, length: int) -> Rejection | None:
        """The offset-0 chunk must show an MP4/QuickTime atom type at bytes 4-7 (T-UV-1)."""
        needed = min(SNIFF_BYTES, length)
        if len(first_bytes) < max(needed, 8):
            return Rejection.NOT_A_VIDEO
        return None if first_bytes[4:8] in TOP_LEVEL_ATOMS else Rejection.NOT_A_VIDEO

    def check(self, facts: MediaFacts) -> Rejection | None:
        """After the probe (§6.6): format first, then length (T-UV-3)."""
        formats = {name.strip() for name in facts.container.split(",")}
        if (
            not formats & set(self.containers)
            or facts.video_codec not in self.video_codecs
            or facts.width * facts.height > self.max_frame_pixels
        ):
            return Rejection.UNSUPPORTED_VIDEO
        if facts.duration_ms > self.max_duration_ms:
            return Rejection.TOO_LONG
        return None
