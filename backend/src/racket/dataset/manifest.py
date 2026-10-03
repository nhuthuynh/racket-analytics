"""Fixture and gold-set manifests and their integrity check (FR-151, NFR-078).

Pure domain code: no I/O and no framework imports (ddd-guidelines §4.5). Callers hash the
files and pass the hashes in as data (see ``racket.dataset.filesystem``).

Rules (testing-strategy §6, QD §8):
* every file in a frozen set is listed in its ``manifest.json`` with its sha256;
* a file whose hash differs from the manifest, an unlisted file or a missing file fails;
* a manifest may change a hash, add or remove a file only together with a higher version.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

ProblemKind = Literal["changed", "unlisted", "missing", "version_not_bumped", "version_decreased"]

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
class Manifest:
    id: str
    version: int
    licence: str
    consent_status: str
    files: Mapping[str, str]
    extra: Mapping[str, Any] = field(default_factory=dict)

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
        extra = {k: v for k, v in data.items() if k not in _REQUIRED}
        return cls(
            id=str(data["id"]),
            version=version,
            licence=str(data["licence"]),
            consent_status=str(data["consent_status"]),
            files=files,
            extra=extra,
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
