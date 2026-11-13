"""The reference read API under test (ST-170b; FR-170.R4, NFR-050.10; ADR 0061 "ACL read side").

The app reads reference content from ``RACKET_REFERENCE_ROOT`` (default: the repository's
``content/references``), with the pattern catalogue and sources register the lint uses
(``RACKET_PATTERN_CATALOGUE``, ``RACKET_SOURCES_REGISTER``; default: ``docs/domain``). The test
suite points the root at ``tests/fixtures/references-api`` (``tests/conftest.py``): one version,
three readable entries (two ``coach-reviewed``, one ``verified``) and one ``draft``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.contract import Seam
from tests.support.paths import BACKEND

ACL = Seam(
    "racket.coaching.reference.acl",
    "ST-170b",
    "ReferenceValue, translate(entry, pattern), readable(reference_set, catalogue)",
)
ROOT_ENV = "RACKET_REFERENCE_ROOT"
CATALOGUE_ENV = "RACKET_PATTERN_CATALOGUE"
SOURCES_ENV = "RACKET_SOURCES_REGISTER"
FIXTURE_ROOT = BACKEND / "tests" / "fixtures" / "references-api"

CURRENT = "/reference-sets/current"
ENTRY = "/reference-sets/{version}/entries/{entry_id}"

READABLE_IDS = ("REF-AN09-D-ADV", "REF-AN09-D-INT", "REF-AN13-D-INT")  # sorted
DRAFT_ID = "REF-AN09-D-BEG"
REVIEWED_ID = "REF-AN09-D-INT"
LABELS = {
    "judgment": "coach judgment, not measured from pro matches",
    "published": "published source",
    "measured": "measured from licensed footage",
}
WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")


def entry_url(entry_id: str, version: int | str = 1) -> str:
    return ENTRY.format(version=version, entry_id=entry_id)


def point_at(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Serve the reference tree at ``root`` (the app reads the variable on each request)."""
    monkeypatch.setenv(ROOT_ENV, str(root))


def without_support_ref(body: object) -> object:
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        return {**body, "error": {k: v for k, v in body["error"].items() if k != "support_ref"}}
    return body
