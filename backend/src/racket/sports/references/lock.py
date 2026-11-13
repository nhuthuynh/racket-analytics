"""Reference-set lock (ST-170a; FR-170.R2): a published version never changes. Pure, stdlib only.

``references.lock`` is ``{"schema": "reference-set-lock/v1", "sets": {"<set>@<N>": sha256}}``,
the sha256 of the version's canonical JSON (the drill library lock rule). Every version file must
be in the lock ("not in lock" until ``--update-lock``), keep its digest ("published version
changed") and keep its file ("published version deleted"). A pull request could rewrite the lock
with the edit, so the base branch's lock is checked too ("lock entry removed", "lock entry
changed"). The lock only grows: ``lock_update`` never replaces a digest.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from racket.sports.references.rules import Problem

LOCK_NAME = "references.lock"
LOCK_SCHEMA = "reference-set-lock/v1"


class LockError(ValueError):
    """A lock file that cannot be read; the CLI exits 2 (fail closed)."""


def digest(doc: object) -> str:
    blob = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def parse_lock(text: str, where: str) -> dict[str, str]:
    try:
        body = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LockError(f"{where}: not JSON ({exc})") from exc
    if not isinstance(body, dict):
        raise LockError(f"{where}: not a {LOCK_SCHEMA} object")
    sets = body.get("sets")
    if body.get("schema") != LOCK_SCHEMA or not isinstance(sets, dict):
        raise LockError(f"{where}: not a {LOCK_SCHEMA} object with sets")
    if not all(isinstance(v, str) for v in sets.values()):
        raise LockError(f"{where}: every digest must be a string")
    return dict(sets)


def render_lock(sets: Mapping[str, str]) -> str:
    return json.dumps({"schema": LOCK_SCHEMA, "sets": dict(sorted(sets.items()))}, indent=2) + "\n"


def _versions(docs: Mapping[str, object]) -> dict[str, tuple[str, str]]:
    """``{"<set>@<N>": (file, digest)}`` from file names ``<set>/v<N>.json``."""
    found = {}
    for file, doc in docs.items():
        set_name, _, version = file.removesuffix(".json").rpartition("/v")
        found[f"{set_name}@{version}"] = (file, digest(doc))
    return found


def check_lock(
    docs: Mapping[str, object], lock: Mapping[str, str], base: Mapping[str, str]
) -> list[Problem]:
    versions = _versions(docs)
    problems = []
    for name, locked in sorted(base.items()):
        if name not in lock:
            problems.append(Problem(LOCK_NAME, name, "version", "lock entry removed"))
        elif lock[name] != locked:
            problems.append(Problem(LOCK_NAME, name, "version", "lock entry changed"))
    expected = {**lock, **base}
    for name, (file, found) in sorted(versions.items()):
        if name not in expected:
            problems.append(Problem(file, name, "version", "not in lock (run --update-lock)"))
        elif expected[name] != found:
            problems.append(Problem(file, name, "version", "published version changed"))
    for name in sorted(set(expected) - set(versions)):
        problems.append(Problem(LOCK_NAME, name, "version", "published version deleted"))
    return problems


def lock_update(docs: Mapping[str, object], lock: Mapping[str, str]) -> dict[str, str]:
    """``lock`` plus the digest of every version it does not have yet."""
    return {name: d for name, (_, d) in _versions(docs).items()} | dict(lock)
