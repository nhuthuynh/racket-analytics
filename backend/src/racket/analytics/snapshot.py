"""``MetricSnapshot``: the starter stats of one match at one score-sheet version (ST-046).

analytics-snapshots.md §2-§5; ADR 0040 (recompute after commit, read repair), ADR 0041 (the
metric dictionary is the only source of the low-sample thresholds). Pure: no I/O, the clock is
passed in. A snapshot is a recomputable read model; the score sheet is the truth (NFR-075).

``starter_stats`` is called through its module (``stats_module.starter_stats``), so a test that
replaces the module attribute reaches this call (IT-03-02 failure injection, §2 "Code layout").
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from racket.analytics import starter_stats as stats_module
from racket.analytics.uncertainty import InvalidPolicy, LowSamplePolicy
from racket.sports.pickleball.metrics import MetricDictionary

# Which ``LowSamplePolicy`` field each metric's ``min_sample`` sets, and the unit it must have.
_THRESHOLDS: dict[str, tuple[str, str]] = {
    "AN-01": ("min_proportion_n", "rallies"),
    "AN-02": ("min_proportion_n", "rallies"),
    "AN-05": ("min_proportion_n", "rallies"),
    "AN-07": ("min_proportion_n", "rallies"),
    "AN-03": ("min_service_turns", "service_turns"),
    "AN-04": ("min_games", "games"),
}
DEFAULT_MAX_INTERVAL_WIDTH = 0.30  # metric-dictionary rule 0.3 (ADR 0005)


def policy_from_dictionary(dictionary: MetricDictionary) -> LowSamplePolicy:
    """The low-sample policy the dictionary defines (ADR 0041). Fails closed when a
    threshold's unit does not fit its metric, or when two metrics that share one policy field
    name different values: the flag would then disagree with the ``min_sample`` on a card."""
    chosen: dict[str, tuple[int, str]] = {}
    for metric, (name, unit) in _THRESHOLDS.items():
        try:
            sample = dictionary.entry(metric).min_sample
        except KeyError:
            continue
        if sample is None:
            raise InvalidPolicy(f"{metric}: min_sample is required")
        if sample.get("unit") != unit:
            raise InvalidPolicy(f"{metric}: min_sample unit must be {unit!r}")
        n = int(sample["n"])
        if name in chosen and chosen[name][0] != n:
            raise InvalidPolicy(f"{metric}: min_sample differs from {chosen[name][1]}")
        chosen.setdefault(name, (n, metric))
    return LowSamplePolicy(
        max_interval_width=DEFAULT_MAX_INTERVAL_WIDTH,
        **{name: n for name, (n, _) in chosen.items()},
    )


@dataclass(frozen=True, slots=True)
class SnapshotKey:
    match_id: uuid.UUID
    metric_def_version: str
    rules_version: str


@dataclass(frozen=True, slots=True)
class MetricSnapshot:
    key: SnapshotKey
    owner_id: uuid.UUID
    sheet_version: int
    stats: Mapping[str, Mapping[str, Mapping[str, Any]]]
    computed_at: datetime

    @classmethod
    def compute(
        cls,
        *,
        match_id: uuid.UUID,
        owner_id: uuid.UUID,
        sheet: Mapping[str, Any],
        sheet_version: int,
        dictionary: MetricDictionary,
        now: datetime,
    ) -> MetricSnapshot:
        """Invariant S1: a pure function of the sheet, the dictionary and the rules version.
        Attribution conservation (S3) is checked inside ``starter_stats``; a violation raises
        and nothing is built."""
        stats = stats_module.starter_stats(sheet, policy_from_dictionary(dictionary))
        key = SnapshotKey(match_id, dictionary.version, str(sheet["rules_version"]))
        return cls(key, owner_id, sheet_version, stats, now)

    def is_behind(self, current_version: int) -> bool:
        return self.sheet_version < current_version

    def published_view(self, dictionary: MetricDictionary) -> dict[str, Any]:
        """Only ``coach-reviewed``/``verified`` entries (FR-102, invariant S5), each with its
        ``public()`` entry and both sides' fields without the ``rallies`` lists."""
        view: dict[str, Any] = {}
        for entry in dictionary.published():
            sides = self.stats.get(entry.id)
            if sides is None:
                continue
            view[entry.id] = {"entry": entry.public()} | {
                side: {k: v for k, v in fields.items() if k != "rallies"}
                for side, fields in sides.items()
            }
        return view

    def rallies(self, metric_id: str, side: str) -> list[int]:
        """The sheet numbers behind one metric and side (FR-103; evidence, §5.4)."""
        return list(self.stats[metric_id][side]["rallies"])
