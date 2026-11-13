"""Reference-set loader (ST-170a; FR-170.R1-R3; ADR 0061 Rule 1): files in, checked values out.

Reads ``<root>/<set>/v<N>.json``, ``<root>/references.lock``, the pattern catalogue (its §1
summary table and §0.8 definition version, until ``patterns.json`` (planned) is published) and
the sources register (§2). ``load_reference_sets`` returns the sets only when every rule and the
lock pass; otherwise it raises ``ReferenceSetRefused`` with every problem (fail closed).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from racket.sports.references.lock import LOCK_NAME, check_lock, parse_lock
from racket.sports.references.rules import Footage, Pattern, Problem, Source, lint_set

DIRECTIONS = frozenset({"higher", "lower", "inside_band"})
_VERSION = re.compile(r"`definition_version` \((\d+(?:\.\d+)*) here\)")
_CELL = re.compile(r"(?<!\\)\|")


class CatalogueError(ValueError):
    """The catalogue or register cannot be read; nothing is accepted (fail closed)."""


class ReferenceSetRefused(ValueError):
    def __init__(self, problems: list[Problem]) -> None:
        super().__init__(f"{len(problems)} reference problem(s)")
        self.problems = problems


@dataclass(frozen=True, slots=True)
class ReferenceEntry:
    id: str
    pattern_id: str
    definition_version: str
    better_direction: str
    level_band: str
    format: str
    source_type: str
    citation_id: str | None
    footage_id: str | None
    status: str
    version: int
    band: tuple[float, float] | None
    value: float | None
    n: int | None
    k: int | None


@dataclass(frozen=True, slots=True)
class ReferenceSet:
    name: str
    version: int
    entries: tuple[ReferenceEntry, ...]


def _table(text: str, heading: str) -> list[dict[str, str]]:
    """The first Markdown table after the line starting with ``heading``, as dicts by header."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(heading)), None)
    rows: list[list[str]] = []
    for line in lines[start + 1 :] if start is not None else []:
        if line.startswith("#"):
            break
        if line.startswith("|"):
            rows.append([c.strip().strip("`") for c in _CELL.split(line.strip())[1:-1]])
        elif rows:
            break
    if len(rows) < 2:
        raise CatalogueError(f"no table after {heading!r}")
    return [dict(zip(rows[0], row, strict=False)) for row in rows[2:]]


def parse_catalogue(text: str) -> dict[str, Pattern]:
    """Ranked patterns (an ``AN-nn`` id and a ``better_direction``) of the catalogue summary."""
    version = _VERSION.search(text)
    if version is None:
        raise CatalogueError("no `definition_version` (N here) line in the catalogue")
    return {
        row["Pattern"]: Pattern(version[1], row["better_direction"], row["interval_method"])
        for row in _table(text, "## 1. Summary")
        if re.fullmatch(r"AN-\d{2}", row.get("Pattern", ""))
        and row.get("better_direction") in DIRECTIONS
    }


def parse_sources(text: str) -> dict[str, Source]:
    return {
        row["Id"]: Source(row.get("Claim kind", ""), row.get("Resolve status", ""))
        for row in _table(text, "## 2. Register")
        if re.fullmatch(r"SRC-\d{4}", row.get("Id", ""))
    }


def read_tree(root: Path) -> tuple[dict[str, object], dict[str, str] | None, list[Problem]]:
    """(version files by ``<set>/v<N>.json``, the lock or None, unreadable-file problems)."""
    docs: dict[str, object] = {}
    broken = []
    for path in sorted(root.rglob("*.json")):
        name = path.relative_to(root).as_posix()
        try:
            docs[name] = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            broken.append(Problem(name, "-", "file", f"invalid json ({exc})"))
    lock_path = root / LOCK_NAME
    lock = None
    if lock_path.exists():
        lock = parse_lock(lock_path.read_text(encoding="utf-8"), str(lock_path))
    return docs, lock, broken


def check_tree(
    docs: Mapping[str, object],
    lock: Mapping[str, str] | None,
    catalogue: Mapping[str, Pattern],
    sources: Mapping[str, Source],
    footage: Mapping[str, Footage],
    base: Mapping[str, str],
) -> list[Problem]:
    problems = [] if lock is not None else [Problem(LOCK_NAME, "-", "lock", "missing")]
    for name, doc in docs.items():
        problems += lint_set(name, doc, catalogue, sources, footage)
    return problems + check_lock(docs, lock or {}, base)


def _entry(e: Mapping[str, Any]) -> ReferenceEntry:
    src, band = e["source"], e.get("band")
    return ReferenceEntry(
        e["id"], e["pattern_id"], e["definition_version"], e["better_direction"],
        e["level_band"], e["format"], e["source_type"], src.get("citation_id"),
        src.get("footage_id"), e["status"], e["version"],
        (band[0], band[1]) if band else None, e.get("value"), e.get("n"), e.get("k"),
    )  # fmt: skip


def load_reference_sets(
    root: Path,
    catalogue: Path,
    sources: Path,
    footage: Mapping[str, Footage] | None = None,
) -> tuple[ReferenceSet, ...]:
    docs, lock, broken = read_tree(root)
    problems = broken + check_tree(
        docs, lock,
        parse_catalogue(catalogue.read_text(encoding="utf-8")),
        parse_sources(sources.read_text(encoding="utf-8")),
        footage or {}, {},
    )  # fmt: skip
    if problems:
        raise ReferenceSetRefused(problems)
    sets = [
        ReferenceSet(doc["set"], doc["version"], tuple(map(_entry, doc["entries"])))
        for doc in docs.values()
        if isinstance(doc, dict)  # every doc is a checked object here (lint_set)
    ]
    return tuple(sorted(sets, key=lambda s: (s.name, s.version)))
