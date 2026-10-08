"""tus checksum and expiration extensions, and the creation metadata (ST-017; api-sprint-01
§6.3-§6.5; threat model T-UV-5, T-UV-6, T-UV-7, T-UV-9). Pure Python.

Every parser here reads untrusted header text: it either returns a value or raises a 4xx
``AppError``; nothing else escapes (retro 0 L4, property-tested).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta

from racket.platform.errors import AppError, BadRequest

ALGORITHMS = {"sha256": 32, "sha1": 20}  # api-sprint-01 §6.1 checksum_algorithms
HEAD_BYTES = 1024 * 1024  # head_sha256 covers min(1 MiB, length) bytes (§6.3)
FILE_NAME_MAX_BYTES = 255
METADATA_KEYS = ("filename", "last_modified", "head_sha256")
_BASE64 = re.compile(r"[A-Za-z0-9+/]+={0,2}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_DECIMAL = re.compile(r"[0-9]{1,20}")
LAST_MODIFIED_MAX = 2**63 - 1  # upload_sessions.file_last_modified_ms is a BIGINT (SEC-R2-S1-01)


class ChecksumInvalid(BadRequest):
    code = "checksum_invalid"


class ChecksumMismatch(AppError):
    """tus checksum extension status 460: nothing of the chunk is stored."""

    status, code = 460, "checksum_mismatch"


class UploadExpired(AppError):
    status, code = 410, "upload_expired"


@dataclass(frozen=True)
class UploadChecksum:
    """``Upload-Checksum: <algorithm> <base64 digest of this request's body>``."""

    algorithm: str
    digest: bytes

    @classmethod
    def parse(cls, raw: str) -> UploadChecksum:
        parts = raw.split(" ")
        if len(parts) != 2 or parts[0] not in ALGORITHMS or not _BASE64.fullmatch(parts[1]):
            raise ChecksumInvalid("malformed or unsupported Upload-Checksum")
        try:
            digest = base64.b64decode(parts[1], validate=True)
        except (binascii.Error, ValueError):
            raise ChecksumInvalid("Upload-Checksum is not base64") from None
        if len(digest) != ALGORITHMS[parts[0]]:
            raise ChecksumInvalid("Upload-Checksum has the wrong length")
        return cls(parts[0], digest)

    def verify(self, data: bytes) -> None:
        if hashlib.new(self.algorithm, data).digest() != self.digest:
            raise ChecksumMismatch("chunk does not match its checksum")


@dataclass(frozen=True)
class ExpiryPolicy:
    """24 h after the last accepted chunk, capped at 72 h after creation (ADR 0006; §6.4)."""

    idle: timedelta
    max_age: timedelta

    def __post_init__(self) -> None:
        if self.idle <= timedelta(0) or self.max_age < self.idle:
            raise ValueError("idle must be positive and max_age at least idle")

    def expires_at(self, *, created_at: datetime, now: datetime) -> datetime:
        return min(now + self.idle, created_at + self.max_age)

    def is_abandoned(
        self, status: str, updated_at: datetime, expires_at: datetime | None, *, now: datetime
    ) -> bool:
        """ST-038 (FR-024, NFR-066 d): the purge frees an upload that is not complete and has
        been idle ``idle`` since its last accepted chunk, or is past its expiry time, or was
        already marked expired. A completed upload is the match's video: never."""
        if status == "complete":
            return False
        if status == "expired":
            return True
        return now - updated_at >= self.idle or (expires_at is not None and now >= expires_at)


DEFAULT_EXPIRY = ExpiryPolicy(idle=timedelta(hours=24), max_age=timedelta(hours=72))


def _clean_name(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    text = "".join(ch for ch in text if unicodedata.category(ch) not in ("Cc", "Cf"))
    encoded = text.encode()[:FILE_NAME_MAX_BYTES]
    return encoded.decode("utf-8", errors="ignore")  # never a split UTF-8 sequence


@dataclass(frozen=True)
class UploadFile:
    """What the client says about the file, for its resume check (display only, T-UV-9):
    never used in object keys, logs, metrics or tool arguments."""

    name: str | None
    last_modified_ms: int | None
    head_sha256: str | None

    @classmethod
    def from_metadata(cls, raw: str | None) -> UploadFile:
        """Reads only ``filename``, ``last_modified`` and ``head_sha256``; other keys are
        ignored and not stored. The overall syntax is checked by the caller first."""
        values: dict[str, bytes] = {}
        for pair in (raw or "").split(","):
            parts = pair.strip().split(" ")
            if len(parts) == 2 and parts[0] in METADATA_KEYS:
                try:
                    values[parts[0]] = base64.b64decode(parts[1], validate=True)
                except (binascii.Error, ValueError):
                    raise BadRequest("malformed Upload-Metadata") from None
        name = _clean_name(values["filename"]) if "filename" in values else None
        modified = None
        if "last_modified" in values:
            text = values["last_modified"].decode("ascii", errors="replace")
            if not _DECIMAL.fullmatch(text):
                raise BadRequest("last_modified must be decimal milliseconds")
            modified = int(text)
            if modified > LAST_MODIFIED_MAX:
                raise BadRequest("last_modified is out of range")
        head = None
        if "head_sha256" in values:
            head = values["head_sha256"].decode("ascii", errors="replace")
            if not _HEX64.fullmatch(head):
                raise BadRequest("head_sha256 must be 64 lower-case hex characters")
        return cls(name or None, modified, head)
