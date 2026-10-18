"""Integration test: the G04-03 golden/property id constants match a real pytest run (FIX-04-1c).

The unit tests check the scorecard's patterns against ``SCORECARD_COMPARISONS``,
``EXTRA_GOLDEN`` and ``PROPERTY_TEST``. This test runs the real marker selections in backend/
and checks those constants are exactly the JUnit ids the runs write, so a renamed test or a
new golden case cannot leave the unit tests checking stale ids.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from domain_budget import junit_outcomes, run_in_backend
from goal_g04_03 import EXTRA_GOLDEN, PROPERTY_TEST, SCORECARD_COMPARISONS

pytestmark = pytest.mark.integration


def _ids(marker: str, tmp_path: Path) -> dict[str, str]:
    report = tmp_path / f"{marker}.xml"
    res = run_in_backend(
        ["uv", "run", "pytest", "-q", "-m", marker, "-p", "no:cacheprovider",
         "--junitxml", str(report)]
    )  # fmt: skip
    assert res.returncode == 0, res.stdout[-2000:]
    return junit_outcomes(report)


def test_the_golden_run_writes_exactly_the_known_ids_all_passed(tmp_path: Path) -> None:
    outcomes = _ids("weakness_golden", tmp_path)
    assert sorted(outcomes) == sorted((*SCORECARD_COMPARISONS, *EXTRA_GOLDEN))
    assert set(outcomes.values()) == {"passed"}


def test_the_property_run_writes_the_property_test_id_passed(tmp_path: Path) -> None:
    assert _ids("plan_property", tmp_path) == {PROPERTY_TEST: "passed"}
