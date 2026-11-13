"""Quick Tag adapter: pattern measures from the starter stats AN-01..AN-07 (ST-171a).

FR-171.R1: ``starter_stats`` and ``uncertainty`` are reused unchanged, so every measure equals
the stat it comes from (IT-06-03). The low-sample policy is the metric dictionary's
(``policy_from_dictionary``, ADR 0041) and each measure carries its dictionary entry's version.
AN-07 is split into its four shares with the plan-target ids of weakness-catalogue §5; a share
keeps AN-07's n and its rule 0.3 flag. AN-03, AN-04 and AN-06 have no interval method, so they
are never rankable (ADR 0061 Rule 3.1). FR-171.R5: a pattern that needs Full Tag facets or a
vision stage is unavailable on a Quick Tag-only match, with the catalogue §0.2 reason.
Replays and undecided rows are match-level exclusions (catalogue §0.2), so n_excluded is 0.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from racket.analytics.patterns.measure import PatternMeasure
from racket.analytics.snapshot import policy_from_dictionary
from racket.analytics.starter_stats import starter_stats
from racket.analytics.uncertainty import Interval
from racket.sports.pickleball.metrics import MetricDictionary

SIDES = ("A", "B")
_PROPORTIONS = ("AN-01", "AN-02", "AN-05")
_SHARES = {
    "AN-07:winner": "winner",
    "AN-07:unforced-error": "unforced_error",
    "AN-07:forced-error": "forced_error",
    "AN-07:fault": "fault",
}
# metric -> (value field, n field) of the starter stat; no interval (ADR 0061 Rule 3.1)
_NO_INTERVAL = {"AN-03": ("value", "turns"), "AN-04": ("value", "games"), "AN-06": ("longest", "n")}
QUICK_TAG_PATTERNS = (*_PROPORTIONS[:2], "AN-03", "AN-04", "AN-05", "AN-06", *_SHARES)
_MISSING_SOURCE = {"FT": "no_shot_facets", "CV": "needs_cv"}

Measures = dict[str, dict[str, PatternMeasure]]


class UnknownDataSource(ValueError):
    """A declared pattern names a data source a Quick Tag-only match cannot lack."""


def _measure(pattern: str, stat: Mapping[str, Any], version: str) -> PatternMeasure:
    """The measure of one side's starter stat ``stat`` (FR-171.R1: same value, n, flag)."""
    if pattern in _NO_INTERVAL:
        value_key, n_key = _NO_INTERVAL[pattern]
        value, n = stat[value_key], stat[n_key]
        return PatternMeasure(pattern, value, n, None, None, stat["low_sample"], version)
    row = stat["shares"][_SHARES[pattern]] if pattern in _SHARES else stat
    low, high = row["ci_low"], row["ci_high"]
    interval = None if low is None else Interval(low, high)
    return PatternMeasure(
        pattern, row["value"], stat["n"], interval, "wilson", stat["low_sample"], version
    )


def quick_tag_measures(
    sheet: Mapping[str, Any],
    dictionary: MetricDictionary,
    *,
    other_patterns: Mapping[str, tuple[str, str]] | None = None,
) -> Measures:
    """``measures[pattern][side]`` for AN-01..AN-07 of one match, then each pattern of
    ``other_patterns`` (``{pattern id: (data source "FT" | "CV", definition version)}``) as
    unavailable, since a Quick Tag match has neither source."""
    stats = starter_stats(sheet, policy_from_dictionary(dictionary))
    out: Measures = {}
    for pattern in QUICK_TAG_PATTERNS:
        metric = pattern.split(":")[0]
        version = dictionary.entry(metric).version
        out[pattern] = {side: _measure(pattern, stats[metric][side], version) for side in SIDES}
    for pattern, (source, version) in (other_patterns or {}).items():
        reason = _MISSING_SOURCE.get(source)
        if reason is None or pattern in out:
            raise UnknownDataSource(f"{pattern}: {source!r} is not a source a match can lack")
        out[pattern] = {
            side: PatternMeasure.unavailable(pattern, reason, version) for side in SIDES
        }
    return out
