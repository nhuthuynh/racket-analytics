"""IT: the G04-03 id constants are exactly the ids of a real marker run (FIX-04-1c)."""

from __future__ import annotations

from pathlib import Path

import pytest
from domain_budget import junit_outcomes
from goal_g04_03 import EXTRA_GOLDEN, PROPERTY_TEST, SCORECARD_COMPARISONS, run_marker

pytestmark = pytest.mark.integration


def _ids(marker: str, tmp_path: Path) -> dict[str, str]:
    report = tmp_path / f"{marker}.xml"
    run_marker(marker, report)
    return junit_outcomes(report)


def test_the_golden_run_writes_exactly_the_known_ids_all_passed(tmp_path: Path) -> None:
    outcomes = _ids("weakness_golden", tmp_path)
    assert sorted(outcomes) == sorted((*SCORECARD_COMPARISONS, *EXTRA_GOLDEN))
    assert set(outcomes.values()) == {"passed"}


def test_the_property_run_writes_the_property_test_id_passed(tmp_path: Path) -> None:
    assert _ids("plan_property", tmp_path) == {PROPERTY_TEST: "passed"}
