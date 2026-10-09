"""The pickleball metric dictionary as data (ST-043; FR-102; NFR-075; Published Language R5).

``metrics.json`` mirrors ``docs/domain/metric-dictionary.md`` (owner: pickleball-domain-coach).
Each entry has an id, a version, the plain-language definition ("How is this measured?"), the
formula text, unit, data level, minimum sample, owner, status and source. Only the coach moves an
entry's status; only ``coach-reviewed`` and ``verified`` entries are published to the stats API
and the UI (FR-102). Changing an entry's definition bumps its version (and the dictionary's);
``metrics.lock.json`` is an append-only record ``{id: {version: digest}}`` of every definition
ever shipped, and ``version_bump_violations`` (pure) reports a definition changed without a bump,
also against the lock on main, so old snapshots keep meaning what they meant (NFR-075).
The top-level ``low_sample`` rule (``max_interval_width``, metric-dictionary rule 0.3; ADR 0041)
is digested too: the lock's ``low_sample`` rows ``{dictionary version: digest}`` record each rule
ever shipped, so changing it needs a new dictionary version.
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
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


LOW_SAMPLE_FIELDS = ("max_interval_width",)


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


def _low_sample(rule: object) -> dict[str, float]:
    """The dictionary-level low-sample rule (ADR 0041): ``{"max_interval_width": w}``,
    0 < w <= 1."""
    if not isinstance(rule, Mapping) or set(rule) != set(LOW_SAMPLE_FIELDS):
        raise InvalidDictionary("low_sample must be {max_interval_width}")
    width = rule["max_interval_width"]
    if isinstance(width, bool) or not isinstance(width, int | float) or not 0 < width <= 1:
        raise InvalidDictionary("low_sample.max_interval_width must be in (0, 1]")
    return {"max_interval_width": float(width)}


@dataclass(frozen=True, slots=True)
class MetricDictionary:
    sport: str
    version: str
    entries: tuple[MetricEntry, ...] = field(default=())
    # Empty only for a dictionary built in code; ``parse`` requires it and the policy refuses
    # a dictionary without it (ADR 0041: no second source of the rule).
    low_sample: Mapping[str, float] = field(default_factory=dict, hash=False)

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
        if "low_sample" not in data:
            raise InvalidDictionary("low_sample is missing (ADR 0041)")
        return cls(sport=_text("dictionary", "sport", data.get("sport")), version=version,
                   entries=entries, low_sample=_low_sample(data["low_sample"]))  # fmt: skip

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


def low_sample_digest(dictionary: MetricDictionary) -> str:
    """sha256 of the dictionary-level low-sample rule (ADR 0041; covered by the lock)."""
    blob = json.dumps(dict(dictionary.low_sample), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


@cache
def load_dictionary() -> MetricDictionary:
    return MetricDictionary.parse(json.loads(METRICS_PATH.read_text(encoding="utf-8")))


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


@dataclass(frozen=True, slots=True)
class DefinitionLock:
    """``metrics.lock.json``: the dictionary version and, per entry, ``{version: digest}`` for
    every definition ever shipped. Append-only: a row is never rewritten or removed."""

    version: str
    entries: Mapping[str, Mapping[str, str]]
    low_sample: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def parse(cls, data: object) -> DefinitionLock:
        if not isinstance(data, Mapping) or not isinstance(data.get("entries"), Mapping):
            raise InvalidDictionary("the lock has no entries object")
        version = data.get("version")
        if not isinstance(version, str) or not _VERSION.match(version):
            raise InvalidDictionary("lock version must look like '0.1'")
        entries: dict[str, dict[str, str]] = {}
        for entry_id, rows in data["entries"].items():
            if not isinstance(rows, Mapping) or not rows:
                raise InvalidDictionary(f"{entry_id}: lock rows must be {{version: digest}}")
            for row_version, digest in rows.items():
                if not isinstance(row_version, str) or not _VERSION.match(row_version):
                    raise InvalidDictionary(f"{entry_id} {row_version}: version")
                if not isinstance(digest, str) or not _DIGEST.match(digest):
                    raise InvalidDictionary(f"{entry_id} {row_version}: digest must be sha256")
            entries[entry_id] = dict(rows)
        rule_rows = data.get("low_sample", {})
        if not isinstance(rule_rows, Mapping):
            raise InvalidDictionary("low_sample lock rows must be {version: digest}")
        for row_version, digest in rule_rows.items():
            if not isinstance(row_version, str) or not _VERSION.match(row_version):
                raise InvalidDictionary(f"low_sample {row_version}: version")
            if not isinstance(digest, str) or not _DIGEST.match(digest):
                raise InvalidDictionary(f"low_sample {row_version}: digest must be sha256")
        return cls(version=version, entries=entries, low_sample=dict(rule_rows))


def version_bump_violations(
    dictionary: MetricDictionary,
    lock: DefinitionLock,
    previous: DefinitionLock | None = None,
) -> tuple[str, ...]:
    """Every way the dictionary breaks NFR-075; empty when it keeps it.

    ``lock`` is the lock next to the dictionary; ``previous`` is the lock on main. Without
    ``previous`` a digest pasted over an existing version is invisible, so CI passes it.
    """
    found: list[str] = []
    if lock.version != dictionary.version:
        found.append(f"dictionary {dictionary.version}: metrics.lock.json is for {lock.version}")
    for entry in dictionary.entries:
        locked = lock.entries.get(entry.id, {}).get(entry.version)
        if locked is None:
            found.append(f"{entry.id} {entry.version}: not recorded in metrics.lock.json")
        elif locked != definition_digest(entry):
            found.append(f"{entry.id} {entry.version}: definition changed without a version bump")
        if _version_key(entry.version) > _version_key(dictionary.version):
            found.append(
                f"dictionary {dictionary.version}: older than entry {entry.id} {entry.version};"
                " bump the dictionary version"
            )
    found.extend(_low_sample_violations(dictionary, lock, previous))
    if previous is None:
        return tuple(found)
    for entry_id, rows in previous.entries.items():
        current_rows = lock.entries.get(entry_id, {})
        for row_version, digest in rows.items():
            if row_version not in current_rows:
                found.append(
                    f"{entry_id} {row_version}: locked row removed; the lock is append-only"
                )
            elif current_rows[row_version] != digest:
                found.append(
                    f"{entry_id} {row_version}: locked digest rewritten; the lock is append-only,"
                    " bump the version"
                )
    added = any(
        version not in previous.entries.get(entry_id, {})
        for entry_id, rows in lock.entries.items()
        for version in rows
    )
    if added and _version_key(lock.version) <= _version_key(previous.version):
        found.append(
            f"dictionary {dictionary.version}: definitions changed since the previous lock"
            f" {previous.version}; bump the dictionary"
        )
    return tuple(found)


def _low_sample_violations(
    dictionary: MetricDictionary, lock: DefinitionLock, previous: DefinitionLock | None
) -> list[str]:
    """The rule in force is the lock row of the newest dictionary version not after the file's;
    a changed rule therefore needs a new row under a new dictionary version (ADR 0041)."""
    found: list[str] = []
    in_force = [v for v in lock.low_sample if _version_key(v) <= _version_key(dictionary.version)]
    if not in_force:
        found.append("low_sample: not recorded in metrics.lock.json")
    elif lock.low_sample[max(in_force, key=_version_key)] != low_sample_digest(dictionary):
        found.append(
            "low_sample: the interval-width rule changed without a dictionary version bump"
        )
    if previous is None:
        return found
    for row_version, digest in previous.low_sample.items():
        if row_version not in lock.low_sample:
            found.append(f"low_sample {row_version}: locked row removed; the lock is append-only")
        elif lock.low_sample[row_version] != digest:
            found.append(
                f"low_sample {row_version}: locked digest rewritten; the lock is append-only,"
                " bump the version"
            )
    return found
