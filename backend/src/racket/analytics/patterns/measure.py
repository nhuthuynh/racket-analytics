"""``PatternMeasure``: one pattern of one side of one match (ST-171a; FR-171.R1, R5, R6).

ADR 0061 Rule 1 (owner: Analytics) and Rule 3.1 (a measure is rankable only with an interval);
``docs/domain/pattern-catalogue.md`` §0.2-§0.3 (unavailable reasons, min_n, interval methods).
Pure: no I/O. The interval is ``racket.analytics.uncertainty.Interval``, unchanged.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from racket.analytics.uncertainty import Interval

INTERVAL_METHODS = ("wilson", "order_statistic_median")
UNAVAILABLE_REASONS = ("no_shot_facets", "no_bounce_positions", "needs_cv")
# an AN id, optionally with a plan-target qualifier (AN-07:fault), or a catalogue word id (STACK)
_PATTERN_ID = re.compile(r"^(AN-\d{2}(:[a-z]+(-[a-z]+)*)?|[A-Z]+)$")
_VERSION = re.compile(r"^\d+\.\d+$")


class InvalidMeasure(ValueError):
    """A measure that breaks its invariants (a programming error, never shown)."""


def _count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


@dataclass(frozen=True, slots=True)
class PatternMeasure:
    pattern_id: str
    value: float | None
    n: int
    interval: Interval | None
    interval_method: str | None
    low_sample: bool
    definition_version: str
    n_excluded: int = 0
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.pattern_id, str) or not _PATTERN_ID.match(self.pattern_id):
            raise InvalidMeasure(f"pattern_id {self.pattern_id!r} is not a pattern id")
        if not isinstance(self.definition_version, str) or not _VERSION.match(
            self.definition_version
        ):
            raise InvalidMeasure(f"definition_version {self.definition_version!r} is not M.m")
        if not _count(self.n):
            raise InvalidMeasure(f"n must be a count, got {self.n!r}")
        if not _count(self.n_excluded):
            raise InvalidMeasure(f"n_excluded must be a count, got {self.n_excluded!r}")
        value = self.value
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int | float) or math.isnan(value)
        ):
            raise InvalidMeasure(f"value must be a number or None, got {value!r}")
        if self.interval_method is not None and self.interval_method not in INTERVAL_METHODS:
            raise InvalidMeasure(f"unknown interval_method {self.interval_method!r}")
        if self.unavailable_reason is not None:
            self._check_unavailable()
        if self.interval is not None and self.interval_method is None:
            raise InvalidMeasure("an interval needs its interval_method")

    def _check_unavailable(self) -> None:
        if self.unavailable_reason not in UNAVAILABLE_REASONS:
            raise InvalidMeasure(f"unknown unavailable reason {self.unavailable_reason!r}")
        sample = (self.value, self.n, self.interval, self.interval_method, self.low_sample)
        if sample != (None, 0, None, None, False) or self.n_excluded:
            # FR-171.R5: never 0, never a sample
            raise InvalidMeasure(f"{self.pattern_id} is unavailable, so it carries no sample")

    @classmethod
    def unavailable(cls, pattern_id: str, reason: str, definition_version: str) -> PatternMeasure:
        """The match lacks the pattern's data source (FR-171.R5): no value, never 0."""
        return cls(pattern_id, None, 0, None, None, False, definition_version,
                   unavailable_reason=reason)  # fmt: skip

    @property
    def available(self) -> bool:
        return self.unavailable_reason is None

    @property
    def rankable(self) -> bool:
        """FR-171.R6 and ADR 0061 Rule 3.1: a value, an interval and not a low sample."""
        return (
            self.available
            and self.value is not None
            and self.interval is not None
            and not self.low_sample
        )
