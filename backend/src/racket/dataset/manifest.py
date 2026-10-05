"""Fixture and gold-set manifests and their integrity check (FR-151, NFR-078).

Pure domain code: no I/O and no framework imports (ddd-guidelines §4.5). Callers hash the
files and pass the hashes in as data (see ``racket.dataset.filesystem``).

Rules (testing-strategy §6, QD §8):
* every file in a frozen set is listed in its ``manifest.json`` with its sha256;
* a file whose hash differs from the manifest, an unlisted file or a missing file fails;
* a manifest may change a hash, add or remove a file only together with a higher version;
* a clip entry (optional ``clips`` list, ST-025) that shows people must carry a consent record
  (OQ-06, ADR 0023): ``shows_people: true`` with a null or blank ``consent_record`` fails.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

ProblemKind = Literal[
    "changed",
    "unlisted",
    "missing",
    "version_not_bumped",
    "version_decreased",
    "consent_missing",
    "clip_not_in_files",
]

_SHA256 = re.compile(r"[0-9a-f]{64}")
_REQUIRED = ("id", "version", "licence", "consent_status", "files")


class ManifestFormatError(ValueError):
    """The manifest itself is malformed."""


def _validate_path(path: object) -> str:
    if not isinstance(path, str) or not path:
        raise ManifestFormatError(f"file path must be a non-empty string, got {path!r}")
    parts = path.split("/")
    if path.startswith("/") or "\\" in path or any(p in ("", ".", "..") for p in parts):
        raise ManifestFormatError(f"file path must be relative and normalised: {path!r}")
    return path


def _validate_sha(path: str, sha: object) -> str:
    if not isinstance(sha, str) or not _SHA256.fullmatch(sha):
        raise ManifestFormatError(f"sha256 for {path!r} must be 64 lower-case hex characters")
    return sha


@dataclass(frozen=True)
class ClipEntry:
    """The consent-relevant facts of one video in a set (ST-025; contract seam phones-v1)."""

    path: str
    shows_people: bool
    consent_record: str | None

    @property
    def consent_missing(self) -> bool:
        return self.shows_people and not (self.consent_record or "").strip()

    @classmethod
    def from_dict(cls, data: object) -> ClipEntry:
        if not isinstance(data, Mapping):
            raise ManifestFormatError(f"clip entry must be an object, got {data!r}")
        for key in ("path", "shows_people", "consent_record"):
            if key not in data:
                raise ManifestFormatError(f"clip entry is missing required field {key!r}")
        path = _validate_path(data["path"])
        shows_people = data["shows_people"]
        if not isinstance(shows_people, bool):
            raise ManifestFormatError(f"shows_people for {path!r} must be true or false")
        consent = data["consent_record"]
        if consent is not None and not isinstance(consent, str):
            raise ManifestFormatError(f"consent_record for {path!r} must be a string or null")
        return cls(path=path, shows_people=shows_people, consent_record=consent)


def _parse_clips(raw: object) -> tuple[ClipEntry, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ManifestFormatError("clips must be a list of clip entries")
    clips = tuple(ClipEntry.from_dict(item) for item in raw)
    paths = [c.path for c in clips]
    if len(set(paths)) != len(paths):
        raise ManifestFormatError("duplicate clip entry path")
    return clips


@dataclass(frozen=True)
class Manifest:
    id: str
    version: int
    licence: str
    consent_status: str
    files: Mapping[str, str]
    extra: Mapping[str, Any] = field(default_factory=dict)
    clips: tuple[ClipEntry, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Manifest:
        for key in _REQUIRED:
            if key not in data:
                raise ManifestFormatError(f"manifest is missing required field {key!r}")
        version = data["version"]
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise ManifestFormatError(f"version must be a positive integer, got {version!r}")
        files: dict[str, str] = {}
        for entry in data["files"]:
            path = _validate_path(entry.get("path"))
            if path in files:
                raise ManifestFormatError(f"duplicate file path {path!r}")
            files[path] = _validate_sha(path, entry.get("sha256"))
        clips = _parse_clips(data.get("clips"))
        extra = {k: v for k, v in data.items() if k not in _REQUIRED}
        return cls(
            id=str(data["id"]),
            version=version,
            licence=str(data["licence"]),
            consent_status=str(data["consent_status"]),
            files=files,
            extra=extra,
            clips=clips,
        )


@dataclass(frozen=True)
class IntegrityProblem:
    kind: ProblemKind
    path: str

    def describe(self) -> str:
        messages = {
            "changed": "file changed: sha256 differs from the manifest",
            "unlisted": "file is not listed in the manifest",
            "missing": "file listed in the manifest is missing",
            "version_not_bumped": "manifest entry changed without a version bump",
            "version_decreased": "manifest version went backwards",
            "consent_missing": "clip shows people but has no consent record (OQ-06)",
            "clip_not_in_files": "clip entry names a file that is not in the manifest files",
        }
        where = f"{self.path}: " if self.path else ""
        return f"{where}{messages[self.kind]} [{self.kind}]"


@dataclass(frozen=True)
class CheckResult:
    problems: tuple[IntegrityProblem, ...]

    @property
    def passed(self) -> bool:
        return not self.problems


class ManifestCheck:
    """Integrity check for a frozen fixture or gold set."""

    @staticmethod
    def check(manifest: Manifest, actual: Mapping[str, str]) -> CheckResult:
        """Compare the actual file hashes of a set with its manifest."""
        problems: list[IntegrityProblem] = []
        for path in sorted(set(manifest.files) | set(actual)):
            if path not in actual:
                problems.append(IntegrityProblem("missing", path))
            elif path not in manifest.files:
                problems.append(IntegrityProblem("unlisted", path))
            elif actual[path] != manifest.files[path]:
                problems.append(IntegrityProblem("changed", path))
        for clip in sorted(manifest.clips, key=lambda c: c.path):
            if clip.path not in manifest.files:
                problems.append(IntegrityProblem("clip_not_in_files", clip.path))
            if clip.consent_missing:
                problems.append(IntegrityProblem("consent_missing", clip.path))
        return CheckResult(tuple(problems))

    @staticmethod
    def check_version_bump(base: Manifest, head: Manifest) -> CheckResult:
        """A manifest may change its file set only together with a higher version."""
        if head.version < base.version:
            return CheckResult((IntegrityProblem("version_decreased", ""),))
        if head.version > base.version:
            return CheckResult(())
        changed = sorted(
            path
            for path in set(base.files) | set(head.files)
            if base.files.get(path) != head.files.get(path)
        )
        return CheckResult(tuple(IntegrityProblem("version_not_bumped", p) for p in changed))
