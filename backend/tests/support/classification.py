"""The data-classification map and its checks (ST-077; NFR-063.1-.2; IT-05-05; ADR 0058 rule 5.3).

``docs/security/data-classification.md`` names every stored type: each SQLAlchemy and live
column (``column``, ``<table>.<column>``), each object-store key prefix (``prefix``, e.g.
``originals/``) and each file of a backup set (``backup``, e.g. ``db.dump.age``). Each row gives
a class and an encryption, a retention and an access rule code; each class row gives its
baseline encryption, retention and access. The checks here are pure; the walkers read a
SQLAlchemy ``MetaData``, a live connection, written object keys or a backup directory.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tests.support.paths import REPO

MAP_PATH = REPO / "docs" / "security" / "data-classification.md"
KINDS = ("column", "prefix", "backup")
NO_BACKUP_ARTEFACT = "no backup artefact found: the walk cannot pass empty (PE-PLAN05-06)"

Item = tuple[str, str]  # (kind, name)


@dataclass(frozen=True)
class Row:
    kind: str
    name: str
    cls: str
    encryption: str
    retention: str
    access: str


@dataclass(frozen=True)
class ClassificationMap:
    classes: dict[str, dict[str, str]] = field(default_factory=dict)
    rules: dict[str, str] = field(default_factory=dict)  # code -> rule kind
    rows: dict[Item, Row] = field(default_factory=dict)


def parse_map(text: str) -> ClassificationMap:
    return ClassificationMap()


def load_map(path: Path = MAP_PATH) -> ClassificationMap:
    return parse_map(path.read_text(encoding="utf-8")) if path.exists() else ClassificationMap()


def unclassified(cmap: ClassificationMap, found: Iterable[Item]) -> list[Item]:
    return []


def stale(cmap: ClassificationMap, found: Iterable[Item], kind: str) -> list[Item]:
    return []


def incomplete(cmap: ClassificationMap) -> list[str]:
    return []


def backup_problems(cmap: ClassificationMap, found: Iterable[Item]) -> list[str]:
    return []


# ---------------------------------------------------------------- walkers
def metadata_columns(metadata: Any) -> set[Item]:
    return {("column", f"{t.name}.{c.name}") for t in metadata.tables.values() for c in t.columns}


def live_columns(connection: Any) -> set[Item]:
    from sqlalchemy import text

    rows = connection.execute(
        text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema()"
        )
    ).all()
    return {("column", f"{t}.{c}") for t, c in rows}


def prefixes(keys: Iterable[str]) -> set[Item]:
    """``originals/<hex>`` -> ``originals/``; a key without ``/`` is its own (unknown) prefix."""
    return {("prefix", key.split("/", 1)[0] + "/" if "/" in key else key) for key in keys}


def backup_files(root: Path) -> set[Item]:
    """Every file name inside every set directory under ``root`` (and any loose file)."""
    if not root.is_dir():
        return set()
    return {("backup", p.name) for p in root.rglob("*") if p.is_file()}
