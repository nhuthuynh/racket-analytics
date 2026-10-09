"""``MetricSnapshot``: the starter stats of one match at one score-sheet version (ST-046).

analytics-snapshots.md §2-§5; ADR 0040 (recompute after commit, read repair), ADR 0041 (the
metric dictionary is the only source of the low-sample thresholds, per metric). Pure: no I/O,
the clock is passed in. A snapshot is a recomputable read model; the score sheet is the truth
(NFR-075).

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

# The unit each metric's ``min_sample`` must have. Proportion metrics keep their own n
# (``LowSamplePolicy.proportion_n``); AN-03 and AN-04 set their policy field (ADR 0041).
_PROPORTIONS: dict[str, str] = {
    "AN-01": "rallies",
    "AN-02": "rallies",
    "AN-05": "rallies",
    "AN-07": "rallies",
}
_COUNTS: dict[str, tuple[str, str]] = {
    "AN-03": ("min_service_turns", "service_turns"),
    "AN-04": ("min_games", "games"),
}


def _threshold(dictionary: MetricDictionary, metric: str, unit: str) -> int | None:
    try:
        sample = dictionary.entry(metric).min_sample
    except KeyError:
        return None
    if sample is None:
        raise InvalidPolicy(f"{metric}: min_sample is required")
    if sample.get("unit") != unit:
        raise InvalidPolicy(f"{metric}: min_sample unit must be {unit!r}")
    return int(sample["n"])


def policy_from_dictionary(dictionary: MetricDictionary) -> LowSamplePolicy:
    """The low-sample policy the dictionary defines, and nothing else (ADR 0041; invariant S6,
    analytics-snapshots.md §5.2): each proportion metric's flag uses its own entry's
    ``min_sample.n``, AN-03 and AN-04 theirs, and the interval-width rule is the dictionary's
    ``low_sample.max_interval_width``. Fails closed when a threshold's unit does not fit its
    metric or the dictionary has no interval-width rule."""
    width = dictionary.low_sample.get("max_interval_width")
    if width is None:
        raise InvalidPolicy("low_sample.max_interval_width is required (ADR 0041)")
    own = {
        metric: n
        for metric, unit in _PROPORTIONS.items()
        if (n := _threshold(dictionary, metric, unit)) is not None
    }
    counts = {
        name: n
        for metric, (name, unit) in _COUNTS.items()
        if (n := _threshold(dictionary, metric, unit)) is not None
    }
    return LowSamplePolicy(max_interval_width=width, proportion_n=own, **counts)


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
