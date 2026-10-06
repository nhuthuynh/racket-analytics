"""Filesystem adapter for the dataset context: hashes the files of a fixture or gold set and
asks git which of them it tracks or could commit."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path

from racket.dataset.gold_set import GoldSet
from racket.dataset.labels import UnreadableLabels
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


def load_labels(root: Path, gold: GoldSet) -> dict[str, object]:
    """Parsed label documents of a gold set by path; absent files are left out (the
    integrity check reports them), unparsable ones become ``UnreadableLabels``."""
    labels: dict[str, object] = {}
    for label_file in (f for clip in gold.clips for f in clip.label_files):
        path = root / label_file
        if not path.is_file() or path.is_symlink():
            continue
        try:
            labels[label_file] = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            labels[label_file] = UnreadableLabels(str(exc))
    return labels


def git_exposed(root: Path, paths: Iterable[str]) -> frozenset[str]:
    """The ``paths`` (relative to ``root``) that git tracks or does not ignore.

    Outside any git work tree nothing is exposed. ``git check-ignore`` (without
    ``--no-index``) never reports a tracked file as ignored, so a tracked file stays exposed
    even when a ``.gitignore`` matches it. Fails closed: if git is missing or errors, every
    path counts as exposed (SEC-S2-TM-06).
    """
    wanted = sorted(set(paths))
    if not wanted:
        return frozenset()
    git = shutil.which("git")
    if git is None:
        return frozenset(wanted)
    try:
        inside = subprocess.run(  # noqa: S603 - fixed argv; root is the set directory checked
            [git, "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            check=False,
        )
        if inside.returncode != 0 or inside.stdout.strip() != "true":
            return frozenset()
        ignored = subprocess.run(  # noqa: S603 - fixed argv; paths go via stdin
            [git, "-C", str(root), "check-ignore", "-z", "--stdin"],
            input="\0".join(wanted) + "\0",
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return frozenset(wanted)
    if ignored.returncode not in (0, 1):
        return frozenset(wanted)
    return frozenset(wanted) - set(ignored.stdout.split("\0"))
