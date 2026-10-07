"""Drill immutability over versions (ST-053; FR-140 "deprecated, never deleted; edits bump the
version"; QD-DR-02).

``library.lock`` maps every drill version ever added (``id@version``) to the sha256 of its
content. Against the lock, a locked version with no file fails ("deleted drill"), a changed
digest fails ("edited without version bump") and a version the lock does not know fails ("not
in lock") until ``racket-drill-lint --update-lock`` adds it. The lock only grows.
``review_status`` and ``deprecated_by`` are lifecycle fields, outside the digest, so the coach
can review a drill and a newer version can deprecate it without a content change.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from racket.coaching.drills.rules import Problem, key, lint_drills

LOCK_NAME = "library.lock"
LOCK_SCHEMA = "drill-library-lock/v1"
LIFECYCLE_FIELDS = frozenset({"review_status", "deprecated_by"})


def content_digest(drill: Mapping[str, Any]) -> str:
    content = {k: v for k, v in drill.items() if k not in LIFECYCLE_FIELDS}
    blob = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def _versions(docs: Mapping[str, object]) -> dict[str, tuple[str, Mapping[str, Any]]]:
    """``id@version -> (source, drill)`` for every document that has an id and a version."""
    found: dict[str, tuple[str, Mapping[str, Any]]] = {}
    for src in sorted(docs):
        doc = docs[src]
        if isinstance(doc, dict) and isinstance(doc.get("id"), str) and "version" in doc:
            found.setdefault(key(doc), (src, doc))
    return found


def lock_entries(drills: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    return {key(d): content_digest(d) for d in drills}


def lock_problems(docs: Mapping[str, object], lock: Mapping[str, str]) -> list[Problem]:
    problems: list[Problem] = []
    versions = _versions(docs)
    for name, (src, drill) in versions.items():
        if name not in lock:
            problems.append(Problem(src, drill["id"], "not in lock", "run with --update-lock"))
        elif lock[name] != content_digest(drill):
            detail = f"{name} differs from {LOCK_NAME}; add a new version instead"
            problems.append(Problem(src, drill["id"], "edited without version bump", detail))
    for gone in sorted(set(lock) - set(versions)):
        detail = f"{gone} is in {LOCK_NAME} but has no file (deprecate, never delete)"
        problems.append(Problem(LOCK_NAME, gone.rpartition("@")[0], "deleted drill", detail))
    return problems


def check_library(
    docs: Mapping[str, object], metrics: frozenset[str], lock: Mapping[str, str]
) -> list[Problem]:
    """The FR-140 rules plus the immutability rules against ``lock``."""
    return lint_drills(docs, metrics) + lock_problems(docs, lock)


def lock_update(
    docs: Mapping[str, object], metrics: frozenset[str], lock: Mapping[str, str]
) -> dict[str, str] | None:
    """The lock with every new drill version added, or None when the lock may not grow: it only
    gains entries, and only when "not in lock" is the library's only problem."""
    problems = check_library(docs, metrics, lock)
    if not problems or any(p.reason != "not in lock" for p in problems):
        return None
    return {**lock_entries(d for _, d in _versions(docs).values()), **lock}


def read_lock(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != LOCK_SCHEMA:
        raise ValueError(f"{path}: not a {LOCK_SCHEMA} file")
    drills = data.get("drills")
    if not isinstance(drills, dict) or not all(isinstance(v, str) for v in drills.values()):
        raise ValueError(f"{path}: 'drills' must map id@version to a sha256")
    return drills


def write_lock(path: Path, drills: Mapping[str, str]) -> None:
    body = {"schema": LOCK_SCHEMA, "drills": dict(sorted(drills.items()))}
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
