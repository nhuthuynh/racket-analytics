"""Reference read routes (ST-170b; FR-170.R4, NFR-050.10; SEC-6 T6-PL-3, T6-PL-4, T6-PL-6).

``GET /reference-sets/current`` lists the current set's readable entries (``acl.readable``);
``GET /reference-sets/{version}/entries/{entry_id}`` reads one entry of any published version of
that set. Signed-in only (401). A draft, unknown or malformed version or id is the same 404
(T6-PL-3). There is no write route (405, T6-PL-4); content changes only by a reviewed PR.
``Cache-Control: no-store`` comes with every answer (``racket.platform.http.SECURITY_HEADERS``).

Content comes from ``RACKET_REFERENCE_ROOT`` (default: the repository's ``content/references``),
checked by the ST-170a loader against the pattern catalogue and the sources register
(``RACKET_PATTERN_CATALOGUE``, ``RACKET_SOURCES_REGISTER``; default: ``docs/domain``). A tree
the loader refuses serves nothing (fail closed) and is logged.
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict
from functools import cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from racket.coaching.reference.acl import ReferenceValue, current, readable
from racket.platform.errors import NotFound
from racket.players.api import CurrentAccount
from racket.sports.references.loader import (
    ReferenceSet,
    ReferenceSetRefused,
    load_reference_sets,
    parse_catalogue,
)
from racket.sports.references.lock import LOCK_NAME

log = logging.getLogger("racket.coaching")
router = APIRouter()
ROOT_ENV = "RACKET_REFERENCE_ROOT"
CATALOGUE_ENV = "RACKET_PATTERN_CATALOGUE"
SOURCES_ENV = "RACKET_SOURCES_REGISTER"
CURRENT_PATH = "/reference-sets/current"
ENTRY_PATH = "/reference-sets/{version}/entries/{entry_id}"

Published = tuple[tuple[ReferenceSet, tuple[ReferenceValue, ...]], ...]


def _repo_file(*parts: str) -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "content" / "references" / LOCK_NAME).is_file():
            return parent.joinpath(*parts)
    return Path(*parts)  # not found: the loader refuses it (fail closed)


def reference_paths() -> tuple[Path, Path, Path]:
    """(content root, pattern catalogue, sources register), read on each request."""
    env = os.environ.get
    root = env(ROOT_ENV) or _repo_file("content", "references")
    catalogue = env(CATALOGUE_ENV) or _repo_file("docs", "domain", "pattern-catalogue.md")
    sources = env(SOURCES_ENV) or _repo_file("docs", "domain", "sources.md")
    return Path(root), Path(catalogue), Path(sources)


def published() -> Published:
    """Each version of the current set with its readable values; empty when the tree is refused."""
    root, catalogue, sources = reference_paths()
    try:
        stamp = (root / LOCK_NAME).stat().st_mtime_ns
    except OSError:
        stamp = -1
    return _load(root, catalogue, sources, stamp)


@cache
def _load(root: Path, catalogue: Path, sources: Path, _stamp: int) -> Published:
    try:
        sets = load_reference_sets(root, catalogue, sources)
        patterns = parse_catalogue(catalogue.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # CatalogueError, LockError, ReferenceSetRefused
        problems = len(exc.problems) if isinstance(exc, ReferenceSetRefused) else 1
        log.error(
            "reference content refused",
            extra={"event": "reference.refused", "problems": problems, "root": str(root)},
        )
        return ()
    newest = current(sets)
    if newest is None:
        return ()
    return tuple((s, readable(s, patterns)) for s in sets if s.name == newest.name)


def _entry_body(value: ReferenceValue) -> dict[str, Any]:
    body = asdict(value)
    for key in ("band", "interval"):
        body[key] = list(body[key]) if body[key] is not None else None
    return body


def _error(description: str) -> dict[str, Any]:
    return {"description": description, "content": {"application/json": {}}}


@router.get(
    CURRENT_PATH,
    summary="Read the current reference set (coach-reviewed and verified entries only)",
    responses={
        200: _error("The set name, its version and its readable entries"),
        401: _error("unauthenticated"),
        404: _error("not_found: no reference set is published"),
    },
)
def get_current_reference_set(account: CurrentAccount) -> dict[str, Any]:
    versions = published()
    if not versions:
        raise NotFound("no reference set")
    newest, values = versions[-1]
    return {
        "set": newest.name,
        "version": newest.version,
        "entries": [_entry_body(v) for v in values],
    }


@router.get(
    ENTRY_PATH,
    summary="Read one coach-reviewed or verified reference entry of a published version",
    responses={
        200: _error("The entry and its set name"),
        401: _error("unauthenticated"),
        404: _error("not_found: the same answer for a draft, unknown or malformed id"),
    },
)
def get_reference_entry(account: CurrentAccount, version: str, entry_id: str) -> dict[str, Any]:
    for reference_set, values in published():
        if str(reference_set.version) != version:
            continue
        for value in values:
            if value.id == entry_id:
                return {"set": reference_set.name, **_entry_body(value)}
    raise NotFound("reference entry")
