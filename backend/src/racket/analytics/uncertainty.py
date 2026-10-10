"""Uncertainty of a starter stat: the Wilson interval and the low-sample rule (ST-044).

FR-101; ADR 0005 (Proposed, thresholds are coach judgment); metric-dictionary rule 0.3. Pure
stdlib: no I/O, clock or randomness. Thresholds are values of ``LowSamplePolicy``; at the
composition root they come from the versioned metric dictionary only (ADR 0041,
``racket.analytics.snapshot.policy_from_dictionary``), never from environment settings.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

Z95 = 1.959963984540054  # two-sided 95% normal quantile


class ImpossibleCounts(ValueError):
    """k and n are not counts of successes among trials (a programming error)."""


class InvalidPolicy(ValueError):
    """A low-sample threshold outside its meaningful range (refused at start-up)."""


def _count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


@dataclass(frozen=True, slots=True)
class Interval:
    low: float
    high: float

    @property
    def width(self) -> float:
        return self.high - self.low


def wilson(k: int, n: int, z: float = Z95) -> Interval | None:
    """95% Wilson score interval for ``k`` successes in ``n`` trials; ``None`` when n = 0.

    The bounds are exactly 0 at k = 0 and exactly 1 at k = n, so a float edge never shows
    "0.0000001" for a side that never won (ADR 0005)."""
    if not (_count(k) and _count(n)) or k > n:
        raise ImpossibleCounts(f"impossible counts k={k!r}, n={n!r}")
    if n == 0:
        return None
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    low = 0.0 if k == 0 else max(0.0, centre - half)
    high = 1.0 if k == n else min(1.0, centre + half)
    return Interval(low, high)


@dataclass(frozen=True, slots=True)
class LowSamplePolicy:
    """When a stat is shown as "low sample" (FR-101). Flagged stats are de-emphasised, never
    hidden. Defaults are ADR 0005's: n >= 20, interval width <= 30 points, >= 2 games for a
    count metric, >= 10 service turns for AN-03 (QD §3.2). ``proportion_n`` holds each
    proportion metric's own minimum n (ADR 0041, invariant S6); a metric without one uses
    ``min_proportion_n``."""

    min_proportion_n: int = 20
    max_interval_width: float = 0.30
    min_games: int = 2
    min_service_turns: int = 10
    proportion_n: Mapping[str, int] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        for name in ("min_proportion_n", "min_games", "min_service_turns"):
            value = getattr(self, name)
            if not _count(value) or value < 1:
                raise InvalidPolicy(f"{name} must be an integer >= 1")
        if not isinstance(self.proportion_n, Mapping):
            raise InvalidPolicy("proportion_n must map a metric id to an integer >= 1")
        for metric, value in self.proportion_n.items():
            if not _count(value) or value < 1:
                raise InvalidPolicy(f"{metric}: minimum n must be an integer >= 1")
        object.__setattr__(self, "proportion_n", MappingProxyType(dict(self.proportion_n)))
        width = self.max_interval_width
        if isinstance(width, bool) or not isinstance(width, int | float) or not 0 < width <= 1:
            raise InvalidPolicy("max_interval_width must be in (0, 1]")

    def proportion_threshold(self, metric: str | None = None) -> int:
        """The minimum n of ``metric`` (its own, else ``min_proportion_n``)."""
        if metric is None:
            return self.min_proportion_n
        return self.proportion_n.get(metric, self.min_proportion_n)

    def proportion_flagged(self, k: int, n: int, metric: str | None = None) -> bool:
        ci = wilson(k, n)
        if ci is None or n < self.proportion_threshold(metric):
            return True
        return ci.width > self.max_interval_width

    def count_flagged(self, *, games: int) -> bool:
        return games < self.min_games

    def turns_flagged(self, turns: int) -> bool:
        return turns < self.min_service_turns
