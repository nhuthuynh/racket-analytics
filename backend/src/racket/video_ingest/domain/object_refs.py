"""Typed object references the purge may delete (SEC-S3-TM-01 / T-DL-3; deletion-and-purge.md
§4.6; ADR 0045). Pure. Each constructor checks the generated-name shape of ``ObjectKeyPolicy``
with a full match and raises ``UnsafeObjectRef`` otherwise, so a row that holds any other text
can never reach a store delete."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

ORIGINAL = re.compile(r"originals/[0-9a-f]{32}")
STAGING_PREFIX = re.compile(r"staging/[0-9a-f]{32}/")
STAGING_CHUNK = re.compile(r"staging/[0-9a-f]{32}/[0-9]{20}")


class UnsafeObjectRef(ValueError):
    """A stored key that is not one of the server's generated names, or one another match
    also names. The purge refuses the whole match (fail closed)."""


def _full(pattern: re.Pattern[str], value: object) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise UnsafeObjectRef("not a generated object name")
    return value


@dataclass(frozen=True, slots=True)
class OriginalKey:
    key: str

    def __post_init__(self) -> None:
        _full(ORIGINAL, self.key)


@dataclass(frozen=True, slots=True)
class StagingPrefix:
    prefix: str

    def __post_init__(self) -> None:
        _full(STAGING_PREFIX, self.prefix)

    @classmethod
    def of(cls, upload_id: uuid.UUID) -> StagingPrefix:
        """Built from the upload id, never from a text column."""
        if not isinstance(upload_id, uuid.UUID):
            raise UnsafeObjectRef("an upload id is a UUID")
        return cls(f"staging/{upload_id.hex}/")


@dataclass(frozen=True, slots=True)
class MultipartRef:
    key: str
    upload_id: str

    def __post_init__(self) -> None:
        if ORIGINAL.fullmatch(str(self.key)) is None:
            _full(STAGING_CHUNK, self.key)
        if not isinstance(self.upload_id, str) or not self.upload_id:
            raise UnsafeObjectRef("a multipart upload needs its id")


ObjectRef = OriginalKey | StagingPrefix | MultipartRef
