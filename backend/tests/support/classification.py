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

    @property
    def rules(self) -> dict[str, str]:
        return {"encryption": self.encryption, "retention": self.retention, "access": self.access}


@dataclass(frozen=True)
class ClassificationMap:
    classes: dict[str, dict[str, str]] = field(default_factory=dict)
    rules: dict[str, str] = field(default_factory=dict)  # code -> rule kind
    rows: dict[Item, Row] = field(default_factory=dict)


RULE_KINDS = ("encryption", "retention", "access")
CLASS_HEADER = ["Class", "Holds", "Encryption", "Retention", "Access"]
RULE_HEADER = ["Code", "Kind", "Rule"]
ROW_HEADER = ["Kind", "Name", "Class", "Encryption", "Retention", "Access"]


def _cells(line: str) -> list[str]:
    return [c.strip().strip("`*").strip() for c in line.strip().strip("|").split("|")]


def parse_map(text: str) -> ClassificationMap:
    """Read the three table shapes by their header row; any other table is prose."""
    cmap, header = ClassificationMap(), None
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            header = None
            continue
        cells = _cells(line)
        if header is None:
            header = cells
        elif set("".join(cells)) <= set("-: "):
            continue
        elif header == CLASS_HEADER:
            cmap.classes[cells[0]] = dict(zip(RULE_KINDS, cells[2:5], strict=True))
        elif header == RULE_HEADER:
            cmap.rules[cells[0]] = cells[1]
        elif header == ROW_HEADER:
            row = Row(*cells[:6])
            cmap.rows[(row.kind, row.name)] = row
    return cmap


def load_map(path: Path = MAP_PATH) -> ClassificationMap:
    return parse_map(path.read_text(encoding="utf-8")) if path.exists() else ClassificationMap()


def unclassified(cmap: ClassificationMap, found: Iterable[Item]) -> list[Item]:
    return sorted(item for item in set(found) if item not in cmap.rows)


def stale(cmap: ClassificationMap, found: Iterable[Item], kind: str) -> list[Item]:
    """Rows of ``kind`` naming nothing the walk found (a dropped column, a renamed file)."""
    seen = set(found)
    return sorted(item for item in cmap.rows if item[0] == kind and item not in seen)


def _rule_problems(owner: str, rules: dict[str, str], cmap: ClassificationMap) -> list[str]:
    return [
        f"{owner}: {kind} {code!r} is not a defined {kind} rule"
        for kind, code in rules.items()
        if cmap.rules.get(code) != kind
    ]


def incomplete(cmap: ClassificationMap) -> list[str]:
    """NFR-063.2: every class and row has a known class and a defined rule of each kind."""
    problems: list[str] = []
    for name, rules in cmap.classes.items():
        problems += _rule_problems(f"class {name}", rules, cmap)
    for row in cmap.rows.values():
        if row.kind not in KINDS:
            problems.append(f"{row.name}: kind {row.kind!r} is not one of {', '.join(KINDS)}")
        elif row.cls not in cmap.classes:
            problems.append(f"{row.name}: class {row.cls!r} is not defined")
        else:
            problems += _rule_problems(row.name, row.rules, cmap)
    return problems


def backup_problems(cmap: ClassificationMap, found: Iterable[Item]) -> list[str]:
    """Zero artefacts is a failure (PE-PLAN05-06); otherwise every file must have a row."""
    items = set(found)
    if not items:
        return [NO_BACKUP_ARTEFACT]
    return [f"unclassified backup artefact: {name}" for _, name in unclassified(cmap, items)]


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
