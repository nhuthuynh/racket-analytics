"""Crafted media for upload-validation tests (ST-018; IT-01-09). Built from the committed
synthetic clip at test time, so no large or third-party file enters the repository."""

from __future__ import annotations

from tests.support.paths import LONG_4H_CLIP, SYNTHETIC_CLIP

PDF_HEAD = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
ELF_HEAD = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8 + b"\x02\x00\x3e\x00\x01\x00\x00\x00"


def pdf_bytes(size: int = 64 * 1024) -> bytes:
    """A PDF-looking file (what 'a PDF renamed to match.mp4' contains)."""
    return (PDF_HEAD * (size // len(PDF_HEAD) + 1))[:size]


def executable_bytes(size: int = 64 * 1024) -> bytes:
    """An ELF executable header (what 'a program renamed to match.mov' contains)."""
    return (ELF_HEAD + b"\x90" * size)[:size]


def long_clip_bytes() -> bytes:
    """A real 4-hour MP4 (fixtures/clips/long-4h, ~200 KB): 'a 4-hour video'."""
    return LONG_4H_CLIP.read_bytes()


def valid_clip_bytes() -> bytes:
    """The 60 s 1080p60 H.264 phone-like fixture: the positive control."""
    return SYNTHETIC_CLIP.read_bytes()
