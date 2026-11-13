"""One frozen measure vector against the product extractor (shared by the AN-xx golden files)."""

from __future__ import annotations

from typing import Any

import pytest

from tests.regression.golden_patterns import support
from tests.support.contract import Seam


def check(seam: Seam, pattern: str, match: str, side: str, extra: tuple[str, ...] = ()) -> None:
    data = support.load(support.MEASURES)
    tol = float(data["tolerance_abs"])
    want: dict[str, Any] = data["measures"][match][side][pattern]
    full_tag_measures = seam.load()
    measures = full_tag_measures(support.labels(match))
    if pattern not in measures:
        pytest.fail(f"{match} side {side}: the product returns no {pattern}", pytrace=False)
    got = support.observed(measures[pattern][side], extra)
    diffs = support.differences(got, support.expected_fields(want, extra), tol)
    assert not diffs, f"{match} side {side} {pattern}: " + "; ".join(diffs)
