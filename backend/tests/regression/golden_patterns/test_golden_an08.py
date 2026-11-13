"""QA-REF-GOLD golden: product AN-08 on GS-PAT-1 equals the frozen vector (FR-171; G06-02).

Frozen by the senior-qa-engineer before the extractor exists (writer/reviewer split, kickoff
QA-3). Each (match, side) is one row; a difference names the match, the side and every field.
Red until ST-171d builds the extractor; the frozen values change only with an ADR
(``golden.lock.json``).
"""

from __future__ import annotations

import pytest

from tests.regression.golden_patterns import _measure_case, seams, support

pytestmark = [pytest.mark.red_until(story="ST-171d"), pytest.mark.golden_patterns]


@pytest.mark.parametrize(("match", "side"), support.measure_cases("AN-08"))
def test_an08_equals_frozen_vector(match: str, side: str) -> None:
    _measure_case.check(seams.AN08, "AN-08", match, side, ())
