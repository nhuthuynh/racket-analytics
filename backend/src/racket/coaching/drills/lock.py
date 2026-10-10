"""Drill immutability over versions (ST-053; FR-140 "deprecated, never deleted; edits bump the
version"; QD-DR-02).

``library.lock`` maps every drill version ever added (``id@version``) to the sha256 of its
content. Against the lock, a locked version with no file fails ("deleted drill"), a changed
digest fails ("edited without version bump") and a version the lock does not know fails ("not
in lock") until ``racket-drill-lint --update-lock`` adds it. The lock only grows.

A PR could delete a file or edit one in place and change ``library.lock`` with it, so the lint
also takes the base branch's lock (``base``; PE-R1-ST053-01): every base entry must still be in
the lock with the same digest ("lock entry removed", "lock entry changed"), and the files are
checked against the base digests, so the deletion or the edit itself fails too.
``review_status`` and ``deprecated_by`` are lifecycle fields, outside the digest, so the coach
can review a drill and a newer version can deprecate it without a content change.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
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


def base_lock_problems(lock: Mapping[str, str], base: Mapping[str, str]) -> list[Problem]:
    """Every entry of the base branch's lock is still in ``lock`` with the same digest."""
    problems: list[Problem] = []
    for name in sorted(base):
        drill = name.rpartition("@")[0]
        if name not in lock:
            detail = f"{name} is locked on the base branch (deprecate, never delete)"
            problems.append(Problem(LOCK_NAME, drill, "lock entry removed", detail))
        elif lock[name] != base[name]:
            detail = f"{name} has another digest on the base branch; add a new version instead"
            problems.append(Problem(LOCK_NAME, drill, "lock entry changed", detail))
    return problems


def check_library(
    docs: Mapping[str, object],
    metrics: frozenset[str],
    lock: Mapping[str, str],
    base: Mapping[str, str] | None = None,
) -> list[Problem]:
    """The FR-140 rules plus the immutability rules against ``lock`` and, when given, the base
    branch's lock ``base`` (its digests win over the lock's)."""
    base = base or {}
    return (
        lint_drills(docs, metrics)
        + lock_problems(docs, {**lock, **base})
        + base_lock_problems(lock, base)
    )


def lock_update(
    docs: Mapping[str, object],
    metrics: frozenset[str],
    lock: Mapping[str, str],
    base: Mapping[str, str] | None = None,
) -> dict[str, str] | None:
    """The lock with every new drill version added, or None when the lock may not grow: it only
    gains entries, and only when "not in lock" is the library's only problem."""
    problems = check_library(docs, metrics, lock, base)
    if not problems or any(p.reason != "not in lock" for p in problems):
        return None
    return {**lock_entries(d for _, d in _versions(docs).values()), **lock}


def parse_lock(text: str, source: str) -> dict[str, str]:
    """The ``id@version -> sha256`` map of a lock file's text; ValueError names ``source``."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source}: not JSON ({exc})") from exc
    if not isinstance(data, dict) or data.get("schema") != LOCK_SCHEMA:
        raise ValueError(f"{source}: not a {LOCK_SCHEMA} file")
    drills = data.get("drills")
    if not isinstance(drills, dict) or not all(isinstance(v, str) for v in drills.values()):
        raise ValueError(f"{source}: 'drills' must map id@version to a sha256")
    return drills


def render_lock(drills: Mapping[str, str]) -> str:
    body = {"schema": LOCK_SCHEMA, "drills": dict(sorted(drills.items()))}
    return json.dumps(body, indent=2) + "\n"
