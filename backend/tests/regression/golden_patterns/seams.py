"""The product entry points the QA-REF-GOLD vectors call (QA-REF-GOLD; ADR 0061 Rule 6).

The vectors were frozen before the extractors (ST-171b/c/d) and the gap rule (ST-172a) exist,
so the entry points are QA proposals, confirmed with the implementing lane at story start
(``tests/support/contract.py``). Changing a seam or ``binding.py`` is a test change (a TCR row
decided by the senior-qa-engineer); changing a frozen vector needs an ADR (``golden.lock.json``).
"""

from __future__ import annotations

from tests.support.contract import Seam

_MEASURES = "racket.analytics.patterns.full_tag:full_tag_measures"
_MEASURES_NOTE = (
    "full_tag_measures(labels: Mapping) -> dict[pattern_id, dict[side, PatternMeasure]] over one "
    "validated full-tag-labels/v1 document, like quick_tag_measures"
)
AN09 = Seam(_MEASURES, "ST-171b", _MEASURES_NOTE + "; AN-09 third-shot drop share")
AN13 = Seam(_MEASURES, "ST-171c", _MEASURES_NOTE + "; AN-13 with PatternMeasure.n_censored")
AN08 = Seam(_MEASURES, "ST-171d", _MEASURES_NOTE + "; AN-08 return depth")
GAP_CASE = Seam(
    "racket.coaching.weakness.reference_gap:conformance_case",
    "ST-172a",
    "conformance_case(case: Mapping) -> Mapping: one gaps vector case (its 'rows') in, "
    "{'results': [...], 'order': [...]} out, as the port runs it (ADR 0061 Rule 6)",
)
