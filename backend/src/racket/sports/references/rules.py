"""Reference-set entry rules (ST-170a; FR-170.R1, R3; ADR 0061 Rules 1 and 3.3). Pure, stdlib only.

A version file ``<set>/v<N>.json`` is ``{"schema": "reference-set/v1", "set", "version",
"entries": [...]}``. Every entry has ``id``, ``pattern_id``, ``definition_version``,
``better_direction`` (equal to the pattern catalogue's), ``level_band``, ``format``,
``source_type``, ``source``, ``status`` and ``version`` (the set's). By source type:

* ``judgment``: ``source.citation_id`` is a row of the sources register; a ``band`` and no n;
  never level band ``pro`` (no pro claim without a pro source).
* ``published``: the citation is a ``resolved`` row of kind ``statistic``; ``value`` and ``n``;
  a ``wilson`` pattern needs ``k`` with value = k/n (the reader computes the interval from k and
  n, so it is never hand-typed); an ``order_statistic_median`` pattern needs ``interval``.
* ``measured``: as published, but the source is ``footage_id`` + ``rights_record_id`` whose
  provenance record permits "reference-library". No record is committed in Sprint 6 (ADR 0062
  planned), so the CLI passes none and every measured entry is refused (fail closed).

An ``inside_band`` pattern always needs a ``band``. Each problem names the file, entry and field.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

SCHEMA = "reference-set/v1"
STATUSES = frozenset({"draft", "coach-reviewed", "verified"})  # ADR 0044 ladder
FORMATS = frozenset({"singles", "doubles"})
LEVEL_BANDS = frozenset({"beginner", "intermediate", "advanced", "pro"})
SOURCE_TYPES = frozenset({"judgment", "published", "measured"})
REFERENCE_LIBRARY = "reference-library"
REQUIRED = (
    "id", "pattern_id", "definition_version", "better_direction", "level_band", "format",
    "source_type", "source", "status", "version",
)  # fmt: skip
_VOCAB = {
    "status": STATUSES,
    "format": FORMATS,
    "level_band": LEVEL_BANDS,
    "source_type": SOURCE_TYPES,
}
_FILE = re.compile(r"^(?P<set>[a-z0-9][a-z0-9-]*)/v(?P<version>[1-9][0-9]*)\.json$")


@dataclass(frozen=True, slots=True)
class Pattern:
    definition_version: str
    better_direction: str
    interval_method: str


@dataclass(frozen=True, slots=True)
class Source:
    kind: str
    status: str


@dataclass(frozen=True, slots=True)
class Footage:
    rights_record_id: str
    permitted_uses: frozenset[str]


@dataclass(frozen=True, slots=True)
class Problem:
    file: str
    entry: str
    field: str
    reason: str

    def __str__(self) -> str:
        return f"FAIL {self.file}: {self.entry}: {self.field}: {self.reason}"


def _number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _pair(value: object) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(_number(v) for v in value)


def _source_problems(
    e: Mapping[str, Any], sources: Mapping[str, Source], footage: Mapping[str, Footage]
) -> list[tuple[str, str]]:
    src, kind = e["source"], e["source_type"]
    if not isinstance(src, dict):
        return [("source", "must be an object")]
    if kind == "measured":
        fid, rid = src.get("footage_id"), src.get("rights_record_id")
        if not (isinstance(fid, str) and fid and isinstance(rid, str) and rid):
            return [("source", "measured needs footage_id and rights_record_id")]
        record = footage.get(fid)
        permits = record is not None and REFERENCE_LIBRARY in record.permitted_uses
        if not permits or record is None or record.rights_record_id != rid:
            return [("source", f"footage {fid} does not permit {REFERENCE_LIBRARY}")]
        return []
    cid = src.get("citation_id")
    if not isinstance(cid, str) or cid not in sources:
        return [("source", f"unresolved citation {cid}")]
    row = sources[cid]
    if kind == "published" and (row.kind, row.status) != ("statistic", "resolved"):
        return [("source", f"{cid} cannot back a published value")]
    return []


def _band_ok(band: object, proportion: bool) -> bool:
    if not (isinstance(band, list) and _pair(band) and band[0] < band[1]):
        return False
    return not proportion or (band[0] >= 0 and band[1] <= 1)


def _value_problems(e: Mapping[str, Any], pattern: Pattern) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    proportion = pattern.interval_method == "wilson"
    if "band" in e:
        if not _band_ok(e["band"], proportion):
            found.append(("band", "must be [low, high] with low < high"))
    elif pattern.better_direction == "inside_band" or e["source_type"] == "judgment":
        found.append(("band", f"missing field (required for {pattern.better_direction})"))
    if e["source_type"] == "judgment":
        if "n" in e:
            found.append(("n", "judgment entries carry a band and no n"))
        return found
    for field in ("value", "n"):
        if field not in e:
            found.append((field, "missing field"))
    if found:
        return found
    value, n, k, interval = e["value"], e["n"], e.get("k"), e.get("interval")
    if not _number(value):
        return [("value", "must be a number")]
    if not (_count(n) and n > 0):
        return [("n", "must be a positive count")]
    if proportion:
        if not (_count(k) and k <= n):
            return [("k", "must be a count of successes, 0 <= k <= n")]
        if abs(value - k / n) > 5e-4:
            return [("value", "must equal k / n")]
    elif not (
        isinstance(interval, list) and _pair(interval) and interval[0] <= value <= interval[1]
    ):
        return [("interval", "must be [low, high] around value")]
    return []


def _entry_problems(
    e: Mapping[str, Any],
    version: int,
    catalogue: Mapping[str, Pattern],
    sources: Mapping[str, Source],
    footage: Mapping[str, Footage],
) -> list[tuple[str, str]]:
    missing = [(f, "missing field") for f in REQUIRED if f not in e]
    if missing:
        return missing
    bad = [
        (f, f"not one of {sorted(allowed)}") for f, allowed in _VOCAB.items() if e[f] not in allowed
    ]
    if not (isinstance(e["id"], str) and e["id"]):
        bad.append(("id", "must be a non-empty string"))
    if e["version"] != version or not _count(e["version"]):
        bad.append(("version", f"must equal the set version {version}"))
    pattern = catalogue.get(e["pattern_id"])
    if pattern is None:
        bad.append(("pattern_id", "not a ranked pattern of the catalogue"))
    if bad or pattern is None:
        return bad
    found: list[tuple[str, str]] = []
    if e["definition_version"] != pattern.definition_version:
        found.append(("definition_version", f"catalogue has {pattern.definition_version}"))
    if e["better_direction"] != pattern.better_direction:
        expected = pattern.better_direction
        found.append(("better_direction", f"differs from the catalogue ({expected})"))
    if e["source_type"] == "judgment" and e["level_band"] == "pro":
        found.append(("level_band", "a judgment value may not claim pro play"))
    return found + _source_problems(e, sources, footage) + _value_problems(e, pattern)


def lint_set(
    name: str,
    doc: object,
    catalogue: Mapping[str, Pattern],
    sources: Mapping[str, Source],
    footage: Mapping[str, Footage],
) -> list[Problem]:
    """Every rule problem of the version file ``name`` (``<set>/v<N>.json``) holding ``doc``."""
    match = _FILE.match(name)
    if match is None:
        return [Problem(name, "-", "file", "must be <set>/v<N>.json")]
    set_name, version = match["set"], int(match["version"])
    entries = doc.get("entries") if isinstance(doc, dict) else None
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA or not isinstance(entries, list):
        return [Problem(name, "-", "schema", f"must be a {SCHEMA} object with entries")]
    problems = []
    if doc.get("set") != set_name:
        problems.append(Problem(name, "-", "set", f"must equal the folder name {set_name}"))
    if doc.get("version") != version:
        problems.append(Problem(name, "-", "version", f"must equal the file version {version}"))
    seen_ids: set[object] = set()
    seen_keys: set[tuple[object, ...]] = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            problems.append(Problem(name, f"entries[{i}]", "entry", "must be an object"))
            continue
        eid = str(e.get("id") or f"entries[{i}]")
        found = _entry_problems(e, version, catalogue, sources, footage)
        if e.get("id") in seen_ids:
            found.append(("id", "duplicate id"))
        key = tuple(e.get(f) for f in ("pattern_id", "level_band", "format"))
        if key in seen_keys:
            found.append(("entry", "duplicate entry ({}, {}, {}, v{})".format(*key, version)))
        seen_ids.add(e.get("id"))
        seen_keys.add(key)
        problems += [Problem(name, eid, field, reason) for field, reason in found]
    return problems
