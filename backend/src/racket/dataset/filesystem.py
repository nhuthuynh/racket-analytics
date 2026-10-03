"""Filesystem adapter for the dataset context: hashes the files of a fixture or gold set."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from racket.dataset.manifest import Manifest

MANIFEST_NAME = "manifest.json"
_CHUNK = 1024 * 1024


class SymlinkInSetError(ValueError):
    """Sets must contain regular files only, so a link cannot smuggle in other content."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def hash_set(root: Path) -> dict[str, str]:
    """Return {posix relative path: sha256} for every file under ``root`` except the manifest."""
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise SymlinkInSetError(rel)
        if path.is_file() and rel != MANIFEST_NAME:
            hashes[rel] = sha256_file(path)
    return hashes


def load_manifest(path: Path) -> Manifest:
    return Manifest.from_dict(json.loads(path.read_text(encoding="utf-8")))
