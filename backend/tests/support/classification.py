"""The data-classification map and its checks (ST-077; NFR-063.1-.2; IT-05-05; ADR 0058 rule 5.3).

``docs/security/data-classification.md`` names every stored type: each SQLAlchemy and live
column (``column``, ``<table>.<column>``), each object-store key prefix (``prefix``, e.g.
``originals/``) and each file of a backup set (``backup``, e.g. ``db.dump.age``). Each row gives
a class and an encryption, a retention and an access rule code; each class row gives its
baseline encryption, retention and access. The checks here are pure; the walkers read a
SQLAlchemy ``MetaData``, a live connection, written object keys or a backup directory.
"""

from __future__ import annotations

import email.utils
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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


SERVER_SIDE = "A-SERVER"


def server_side_returned(
    cmap: ClassificationMap, table: str, row: dict[str, Any], response: Any
) -> list[str]:
    """Columns of one live ``row`` of ``table`` whose value the API ``response`` returned
    although the map marks them ``A-SERVER`` ("no API response returns it", SPE-ST077-01)."""
    leaves = list(_leaves(response))
    return [
        f"{table}.{name} is {SERVER_SIDE} but the API returned it"
        for name, value in sorted(row.items())
        if (row_ := cmap.rows.get(("column", f"{table}.{name}"))) is not None
        and row_.access == SERVER_SIDE
        and _returned(value, leaves)
    ]


def _leaves(value: Any) -> Iterator[Any]:
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _leaves(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _leaves(item)
    else:
        yield value


def _as_time(leaf: Any) -> tuple[datetime, timedelta] | None:
    """An RFC 3339 string or an HTTP-date (tus headers), with the precision of its format:
    ms for the match read model, whole seconds (truncated) for ``retry_at``/``next_slot_at``."""
    if not isinstance(leaf, str):
        return None
    try:
        at = datetime.fromisoformat(leaf.replace("Z", "+00:00"))
    except ValueError:
        pass
    else:
        whole_seconds = "." not in leaf.split("T")[-1]
        return at, timedelta(seconds=1) if whole_seconds else timedelta(milliseconds=1)
    try:
        return email.utils.parsedate_to_datetime(leaf), timedelta(seconds=1)
    except (TypeError, ValueError, IndexError):
        return None


def _returned(value: Any, leaves: list[Any]) -> bool:
    """Whether ``value`` is among the response ``leaves``: an equal number, a string or UUID
    inside a string (an id in ``resume_url``), a timestamp within the precision of its format.
    ``None``, booleans and JSON or bytes columns are never matched (too generic to trace).

    Limit: a timestamp matches by proximity (1 ms, or 1 s for a whole-second RFC 3339 or
    HTTP-date leaf), so a column written in the same instant as a returned one (the probe job
    and ``matches.updated_at``) is reported too. This fails closed (map coverage limits)."""
    if value is None or isinstance(value, bool | bytes | Mapping | list):
        return False
    if isinstance(value, datetime):
        times = [t for t in map(_as_time, leaves) if t is not None and t[0].tzinfo is not None]
        return any(abs(at - value) < precision for at, precision in times)
    if isinstance(value, int):
        return any(
            not isinstance(leaf, bool) and (leaf == value or leaf == str(value)) for leaf in leaves
        )
    text = str(value)
    return len(text) >= 4 and any(isinstance(leaf, str) and text in leaf for leaf in leaves)


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
