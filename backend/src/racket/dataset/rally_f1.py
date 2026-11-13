"""Rally-segmentation F1 matcher (ST-084b; NFR-006.1-.4; ADR 0004 option 3; ADR 0060 row M11).

Pure domain code of the dataset (evaluation) context: rallies arrive as start and end seconds;
no I/O. The rules, from ADR 0004 ("start and end each within ±1.0 s, not merged or split"):

* R1 (NFR-006.1): a prediction may match a gold rally only when its start and its end are each
  within 1.0 s of the gold rally's, compared in whole milliseconds so float noise such as
  ``2.1 - 1.1`` does not turn exactly 1.0 s into a miss.
* R2 (NFR-006.2): a prediction that overlaps two gold rallies which do not overlap each other is
  a merge and matches nothing.
* R3 (NFR-006.3): a gold rally with two pieces that do not overlap each other is a split and
  matches nothing. A piece is a prediction that overlaps the gold rally, lies inside it with the
  1.0 s slack on each side, and is not itself a merge (R2), so a merge or a prediction running
  well past the gold rally does not cancel a correct match. Two predictions that overlap each
  other are duplicates, not pieces, so they fall under R4.
* R4 (NFR-006.4): matching is one-to-one and of maximum size (augmenting paths), so the count
  does not depend on input order.

Precision = TP / predictions, recall = TP / gold rallies, F1 = 2 TP / (predictions + gold),
each 0.0 when its denominator is 0. ``f1_pct`` is F1 in the unit of ADR 0060 row M11 (%).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

TOLERANCE_MS = 1000  # ADR 0004: ±1.0 s on the start and on the end


@dataclass(frozen=True)
class Rally:
    """One rally on the video timeline, in seconds."""

    start_s: float
    end_s: float

    def __post_init__(self) -> None:
        if not (math.isfinite(self.start_s) and math.isfinite(self.end_s)):
            raise ValueError(f"rally times must be finite: {self.start_s}-{self.end_s}")
        if self.end_s <= self.start_s:
            raise ValueError(f"rally must end after it starts: {self.start_s}-{self.end_s}")

    def overlaps(self, other: Rally) -> bool:
        return self.start_s < other.end_s and other.start_s < self.end_s


@dataclass(frozen=True)
class RallyF1:
    """Counts and scores of one matching; ``pairs`` are (prediction, gold) indexes."""

    tp: int
    fp: int
    fn: int
    pairs: tuple[tuple[int, int], ...]

    @property
    def precision(self) -> float:
        return _ratio(self.tp, self.tp + self.fp)

    @property
    def recall(self) -> float:
        return _ratio(self.tp, self.tp + self.fn)

    @property
    def f1(self) -> float:
        return _ratio(2 * self.tp, 2 * self.tp + self.fp + self.fn)

    @property
    def f1_pct(self) -> float:
        return 100 * self.f1


def match_rallies(predicted: Sequence[Rally], gold: Sequence[Rally]) -> RallyF1:
    """Match predicted rallies to gold rallies one-to-one (R1-R4) and score them."""
    if not predicted and not gold:
        raise ValueError("nothing to score: no predicted and no gold rallies")
    candidates = [
        [
            j
            for j, g in enumerate(gold)
            if _within_tolerance(p, g) and not _cut(p, gold) and not _split(g, predicted, gold)
        ]
        for p in predicted
    ]
    gold_to_pred: dict[int, int] = {}
    for i in range(len(predicted)):
        _augment(i, candidates, gold_to_pred, set())
    pairs = tuple(sorted((i, j) for j, i in gold_to_pred.items()))
    tp = len(pairs)
    return RallyF1(tp=tp, fp=len(predicted) - tp, fn=len(gold) - tp, pairs=pairs)


def _within_tolerance(p: Rally, g: Rally) -> bool:
    return (
        round(abs(p.start_s - g.start_s) * 1000) <= TOLERANCE_MS
        and round(abs(p.end_s - g.end_s) * 1000) <= TOLERANCE_MS
    )


def _split(g: Rally, predicted: Sequence[Rally], gold: Sequence[Rally]) -> bool:
    """True when gold rally ``g`` has two pieces that do not overlap each other (R3)."""
    pieces = [p for p in predicted if _piece_of(p, g) and not _cut(p, gold)]
    return any(not a.overlaps(b) for k, a in enumerate(pieces) for b in pieces[k + 1 :])


def _piece_of(p: Rally, g: Rally) -> bool:
    """True when ``p`` overlaps ``g`` and lies inside it, with the 1.0 s slack on each side."""
    return (
        p.overlaps(g)
        and round((g.start_s - p.start_s) * 1000) <= TOLERANCE_MS
        and round((p.end_s - g.end_s) * 1000) <= TOLERANCE_MS
    )


def _cut(rally: Rally, others: Sequence[Rally]) -> bool:
    """True when ``rally`` overlaps two of ``others`` that do not overlap each other."""
    hits = [o for o in others if rally.overlaps(o)]
    return any(not a.overlaps(b) for k, a in enumerate(hits) for b in hits[k + 1 :])


def _augment(
    i: int, candidates: list[list[int]], gold_to_pred: dict[int, int], seen: set[int]
) -> bool:
    """Kuhn's augmenting path from prediction ``i``; updates ``gold_to_pred`` on success."""
    for j in candidates[i]:
        if j in seen:
            continue
        seen.add(j)
        if j not in gold_to_pred or _augment(gold_to_pred[j], candidates, gold_to_pred, seen):
            gold_to_pred[j] = i
            return True
    return False


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0
