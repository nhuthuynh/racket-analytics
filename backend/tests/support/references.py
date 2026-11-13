"""Builders for reference-set trees (ST-170a; FR-170.R1-R3; ADR 0061 Rules 1 and 3.3).

A tree is ``<root>/<set>/v<N>.json`` plus ``<root>/references.lock``. The lock maps
``<set>@<N>`` to the sha256 of the version's canonical JSON (sorted keys, no spaces), the same
digest rule as the drill library lock (``racket.coaching.drills.lock``). The builders write the
digest themselves, so the tests pin the lock format instead of trusting the code under test.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from tests.support.contract import Seam
from tests.support.paths import REPO

LINT = Seam(
    "racket.sports.references.lint:main",
    "ST-170a",
    "main(argv: list[str] | None = None) -> int",
)
RULES = Seam("racket.sports.references.rules", "ST-170a", "lint_set, Pattern, Source, Footage")
LOCK = Seam("racket.sports.references.lock", "ST-170a", "check_lock, digest")
LOADER = Seam("racket.sports.references.loader", "ST-170a", "parse_catalogue, parse_sources")

CATALOGUE = REPO / "docs" / "domain" / "pattern-catalogue.md"
SOURCES = REPO / "docs" / "domain" / "sources.md"
LOCK_NAME = "references.lock"
SET = "pb-reference"

_ENTRY: dict[str, Any] = {
    "id": "REF-AN09-D-INT",
    "pattern_id": "AN-09",
    "definition_version": "0.1",
    "better_direction": "inside_band",
    "level_band": "intermediate",
    "format": "doubles",
    "source_type": "judgment",
    "source": {"citation_id": "SRC-0002"},
    "band": [0.45, 0.70],
    "status": "coach-reviewed",
    "version": 1,
}


def entry(**changes: Any) -> dict[str, Any]:
    """A complete, valid AN-09 judgment entry; ``field=None`` removes the field."""
    made = copy.deepcopy(_ENTRY)
    for key, value in changes.items():
        if value is None:
            made.pop(key, None)
        else:
            made[key] = value
    return made


def reference_doc(entries: Iterable[dict[str, Any]], version: int = 1) -> dict[str, Any]:
    return {
        "schema": "reference-set/v1",
        "set": SET,
        "version": version,
        "entries": [{**e, "version": e.get("version", version)} for e in entries],
    }


def digest(doc: object) -> str:
    blob = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def write_version(root: Path, doc: dict[str, Any], lock: bool = True) -> Path:
    """Write ``doc`` as ``<root>/<set>/v<N>.json``; with ``lock``, add its digest to the lock."""
    path = root / doc["set"] / f"v{doc['version']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    locked = read_lock(root)
    if lock:
        locked[f"{doc['set']}@{doc['version']}"] = digest(doc)
    write_lock(root, locked)
    return path


def read_lock(root: Path) -> dict[str, str]:
    path = root / LOCK_NAME
    if not path.exists():
        return {}
    sets: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))["sets"]
    return sets


def write_lock(root: Path, sets: dict[str, str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    body = {"schema": "reference-set-lock/v1", "sets": dict(sorted(sets.items()))}
    (root / LOCK_NAME).write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def lint_args(root: Path, *extra: str) -> list[str]:
    return [str(root), "--catalogue", str(CATALOGUE), "--sources", str(SOURCES), *extra]
