"""QA-REF-GOLD golden: the gap rule on GS-PAT-1 x golden reference v1 (FR-172.R1-R4; G06-03).

Each case is one player side at one level band and format with the frozen measures as input;
the product must give the frozen state, side, size and rank of every pattern and the frozen
order of weaknesses, and the same output for the rows in reverse order (permutation-stable,
ADR 0061 Rule 3.5). Red until ST-172a builds ``coaching/weakness/reference_gap``.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.regression.golden_patterns import seams, support

pytestmark = [pytest.mark.red_until(story="ST-172a"), pytest.mark.golden_patterns]


def _case_ids() -> list[str]:
    if not support.GAPS.is_file():
        return ["missing-vectors"]
    return [c["id"] for c in json.loads(support.GAPS.read_text(encoding="utf-8"))["cases"]]


def _case(case_id: str) -> tuple[dict[str, Any], float]:
    data = support.load(support.GAPS)
    by_id = {c["id"]: c for c in data["cases"]}
    if case_id not in by_id:
        pytest.fail(f"no frozen gap case {case_id}", pytrace=False)
    return by_id[case_id], float(data["tolerance_abs"])


def _check(got: Any, case: dict[str, Any], tol: float) -> None:
    want = case["expected"]
    assert isinstance(got, dict), f"{case['id']}: product returned {type(got).__name__}"
    assert list(got.get("order", [])) == want["order"], f"{case['id']}: order {got.get('order')}"
    results = {r["pattern_id"]: r for r in got.get("results", [])}
    assert sorted(results) == sorted(r["pattern_id"] for r in want["results"]), case["id"]
    for row in want["results"]:
        diffs = support.differences(results[row["pattern_id"]], row, tol)
        assert not diffs, f"{case['id']} {row['pattern_id']}: " + "; ".join(diffs)


@pytest.mark.parametrize("case_id", _case_ids())
def test_gap_case_equals_frozen_vector(case_id: str) -> None:
    case, tol = _case(case_id)
    conformance_case = seams.GAP_CASE.load()
    _check(conformance_case({"rows": case["rows"]}), case, tol)


@pytest.mark.parametrize("case_id", _case_ids())
def test_gap_case_is_permutation_stable(case_id: str) -> None:
    case, tol = _case(case_id)
    conformance_case = seams.GAP_CASE.load()
    _check(conformance_case({"rows": list(reversed(case["rows"]))}), case, tol)
