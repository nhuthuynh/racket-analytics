"""ST-173b (FR-173.R3): CLI <-> files, ``racket-drill-coverage --patterns``.

The starter library holds no drill targeting AN-09 or AN-13 (ST-173c adds them), so the pattern
axis fails naming the FR-173.R3 negative cell; without ``--patterns`` the existing gated check is
unchanged (rc 0), so ``main`` stays green until ST-173c closes the cells. The cell rules are
unit-tested in ``tests/unit/coaching/test_coverage_patterns.py``. Written red first.
"""

from __future__ import annotations

import pytest

from tests.integration.test_it_04_13_drill_coverage_cli import LIBRARY, fails, run

CELL = "AN-13 × intermediate × 1 player × wall: no fitting drill"


def test_the_pattern_axis_names_the_empty_cells_of_the_starter_library(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc, out = run(capsys, LIBRARY, "--patterns")
    assert rc == 1, out
    found = fails(out)
    assert f"FAIL {CELL}" in found, out
    assert len([f for f in found if f.endswith("no fitting drill")]) == 54, out


def test_without_the_flag_the_starter_library_still_passes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc, out = run(capsys, LIBRARY)
    assert rc == 0, out
    assert "no fitting drill" not in out, out
