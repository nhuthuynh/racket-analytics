"""The pickleball metric dictionary as data (ST-043; FR-102; NFR-075; Published Language R5).

``metrics.json`` mirrors ``docs/domain/metric-dictionary.md`` (owner: pickleball-domain-coach).
Each entry has an id, a version, the plain-language definition ("How is this measured?"), the
formula text, unit, data level, minimum sample, owner, status and source. Only the coach moves an
entry's status; only ``coach-reviewed`` and ``verified`` entries are published to the stats API
and the UI (FR-102). Changing an entry's definition bumps its version (and the dictionary's);
``metrics.lock.json`` holds the digest of every definition, and a unit test fails when a
definition changes without a bump, so old snapshots keep meaning what they meant (NFR-075).
Pure stdlib; reads only its own package file.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

METRICS_PATH = Path(__file__).with_name("metrics.json")
LOCK_PATH = Path(__file__).with_name("metrics.lock.json")
STATUSES = ("draft", "coach-reviewed", "verified", "deprecated")
PUBLISHED = frozenset({"coach-reviewed", "verified"})
DATA_LEVELS = frozenset({"QT"})  # Quick Tag fields only in R1 (FR-050)
FIELDS = (
    "id",
    "version",
    "name",
    "definition",
    "formula",
    "unit",
    "data_level",
    "min_sample",
    "owner",
    "status",
    "source",
)
DEFINITION_FIELDS = ("name", "definition", "formula", "unit", "data_level", "min_sample")
_ID = re.compile(r"^AN-\d{2}$")
_VERSION = re.compile(r"^\d+\.\d+$")


class InvalidDictionary(ValueError):
    """The dictionary file is not valid; the process refuses to start (fail closed)."""


@dataclass(frozen=True, slots=True)
class MetricEntry:
    id: str
    version: str
    name: str
    definition: str
    formula: str
    unit: str
    data_level: str
    min_sample: Mapping[str, Any] | None  # None: descriptive, never flagged (AN-06)
    owner: str
    status: str
    source: str

    @property
    def published(self) -> bool:
        return self.status in PUBLISHED

    def public(self) -> dict[str, Any]:
        """What the stats response and the metric card show."""
        return {
            "id": self.id,
            "version": self.version,
            "name": self.name,
            "definition": self.definition,
            "unit": self.unit,
            "min_sample": None if self.min_sample is None else dict(self.min_sample),
            "status": self.status,
        }


def _text(entry_id: str, name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidDictionary(f"{entry_id}: {name} must be non-empty text")
    return value


def _min_sample(entry_id: str, sample: object) -> dict[str, Any]:
    n = sample.get("n") if isinstance(sample, Mapping) else None
    unit = sample.get("unit") if isinstance(sample, Mapping) else None
    if not (isinstance(n, int) and not isinstance(n, bool) and n >= 1 and isinstance(unit, str)):
        raise InvalidDictionary(f"{entry_id}: min_sample must be null or {{unit, n >= 1}}")
    return {"unit": unit, "n": n}


def _entry(raw: object) -> MetricEntry:
    if not isinstance(raw, Mapping):
        raise InvalidDictionary("an entry is not an object")
    entry_id = raw.get("id")
    if not isinstance(entry_id, str) or not _ID.match(entry_id):
        raise InvalidDictionary(f"bad id {entry_id!r}")
    unknown = sorted(set(raw) - set(FIELDS))
    if unknown:
        raise InvalidDictionary(f"{entry_id}: unknown field {', '.join(unknown)}")
    missing = [name for name in FIELDS if name not in raw]
    if missing:
        raise InvalidDictionary(f"{entry_id}: {', '.join(missing)} missing")
    version = raw["version"]
    if not isinstance(version, str) or not _VERSION.match(version):
        raise InvalidDictionary(f"{entry_id}: version must look like '0.1'")
    if raw["status"] not in STATUSES:
        raise InvalidDictionary(f"{entry_id}: unknown status {raw['status']!r}")
    if raw["data_level"] not in DATA_LEVELS:
        raise InvalidDictionary(f"{entry_id}: data_level must be one of {sorted(DATA_LEVELS)}")
    sample = raw["min_sample"]
    min_sample = None if sample is None else _min_sample(entry_id, sample)
    return MetricEntry(
        id=entry_id,
        version=version,
        name=_text(entry_id, "name", raw["name"]),
        definition=_text(entry_id, "definition", raw["definition"]),
        formula=_text(entry_id, "formula", raw["formula"]),
        unit=_text(entry_id, "unit", raw["unit"]),
        data_level=raw["data_level"],
        min_sample=min_sample,
        owner=_text(entry_id, "owner", raw["owner"]),
        status=raw["status"],
        source=_text(entry_id, "source", raw["source"]),
    )


@dataclass(frozen=True, slots=True)
class MetricDictionary:
    sport: str
    version: str
    entries: tuple[MetricEntry, ...] = field(default=())

    @classmethod
    def parse(cls, data: object) -> MetricDictionary:
        if not isinstance(data, Mapping) or not isinstance(data.get("entries"), list):
            raise InvalidDictionary("the dictionary has no entries list")
        version = data.get("version")
        if not isinstance(version, str) or not _VERSION.match(version):
            raise InvalidDictionary("dictionary version must look like '0.1'")
        entries = tuple(_entry(raw) for raw in data["entries"])
        seen: set[str] = set()
        for entry in entries:
            if entry.id in seen:
                raise InvalidDictionary(f"duplicate id {entry.id}")
            seen.add(entry.id)
        return cls(sport=_text("dictionary", "sport", data.get("sport")), version=version,
                   entries=entries)  # fmt: skip

    def entry(self, entry_id: str) -> MetricEntry:
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        raise KeyError(entry_id)

    def published(self) -> tuple[MetricEntry, ...]:
        return tuple(e for e in self.entries if e.published)

    def is_published(self, entry_id: str) -> bool:
        return any(e.id == entry_id for e in self.published())


def definition_digest(entry: MetricEntry) -> str:
    """sha256 of the fields that define what a metric means (status and source excluded)."""
    payload = {name: getattr(entry, name) for name in DEFINITION_FIELDS}
    payload["min_sample"] = None if entry.min_sample is None else dict(entry.min_sample)
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


@cache
def load_dictionary() -> MetricDictionary:
    return MetricDictionary.parse(json.loads(METRICS_PATH.read_text(encoding="utf-8")))
