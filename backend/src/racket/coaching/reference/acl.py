"""Reference ACL (ST-170b; FR-170.R4, R5; ADR 0061 "ACL read side" and Rule 3.3; map R13).

Published reference entries (``racket.sports.references``) become Coaching's ``ReferenceValue``.
Only ``coach-reviewed`` and ``verified`` entries cross. An entry the ACL cannot translate (an
unknown status or source type, a pattern not in the catalogue, a published or measured value
without an interval it can compute) is dropped, never guessed (fail closed): the pattern then
reads "no reference yet". The footage id of a measured entry does not cross (P16 Q9).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from racket.analytics import public as analytics
from racket.sports.references.loader import ReferenceEntry, ReferenceSet
from racket.sports.references.rules import Pattern

READABLE = frozenset({"coach-reviewed", "verified"})
PROVENANCE_LABELS = {  # flows-sprint-06 C-10, FR-170.R5
    "judgment": "coach judgment, not measured from pro matches",
    "published": "published source",
    "measured": "measured from licensed footage",
}


@dataclass(frozen=True, slots=True)
class ReferenceValue:
    id: str
    pattern_id: str
    definition_version: str
    better_direction: str
    interval_method: str
    level_band: str
    format: str
    source_type: str
    provenance_label: str
    citation_id: str | None
    status: str
    version: int
    value: float | None
    band: tuple[float, float] | None
    n: int | None
    k: int | None
    interval: tuple[float, float] | None


def _interval(entry: ReferenceEntry, pattern: Pattern) -> tuple[float, float] | None:
    """A judgment band is its own interval; a published or measured proportion's is computed
    from k and n (never stored); anything else has none the ACL can vouch for."""
    if entry.source_type == "judgment":
        return entry.band
    if pattern.interval_method == "wilson" and entry.k is not None and entry.n is not None:
        return analytics.wilson_interval(entry.k, entry.n)
    return None


def translate(entry: ReferenceEntry, pattern: Pattern) -> ReferenceValue | None:
    label = PROVENANCE_LABELS.get(entry.source_type)
    if entry.status not in READABLE or label is None:
        return None
    interval = _interval(entry, pattern)
    if interval is None:
        return None
    return ReferenceValue(
        entry.id, entry.pattern_id, entry.definition_version, entry.better_direction,
        pattern.interval_method, entry.level_band, entry.format, entry.source_type, label,
        entry.citation_id if entry.source_type != "measured" else None, entry.status,
        entry.version, entry.value, entry.band, entry.n, entry.k, interval,
    )  # fmt: skip


def readable(
    reference_set: ReferenceSet, catalogue: Mapping[str, Pattern]
) -> tuple[ReferenceValue, ...]:
    """The set's entries that cross the ACL, by id."""
    values = (
        translate(e, catalogue[e.pattern_id])
        for e in reference_set.entries
        if e.pattern_id in catalogue
    )
    return tuple(sorted((v for v in values if v is not None), key=lambda v: v.id))


def current(sets: Iterable[ReferenceSet]) -> ReferenceSet | None:
    """The newest version of the one published set; none when there is no set, or more than one
    set name (which set is "current" would be a guess)."""
    found = tuple(sets)
    if len({s.name for s in found}) != 1:
        return None
    return max(found, key=lambda s: s.version)
