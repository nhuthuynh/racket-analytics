"""CLI binding of tests/features/drill_coverage_patterns.feature (ST-173b; FR-173.R3):
``racket-drill-coverage --patterns`` on copies of ``content/drills``, one with a solo wall and a
solo court drill added for AN-09 and AN-13. Written red first."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.integration.test_it_04_13_drill_coverage_cli import LIBRARY, fails, run
from tests.unit.coaching.drill_helpers import a_drill

scenarios("drill_coverage_patterns.feature")

NEW = ["AN-09", "AN-13"]


def pattern_drill(drill_id: str, needs: list[str]) -> dict[str, Any]:
    """A reviewed solo drill for every level, 8-12 min, hitting both new patterns."""
    return a_drill(
        drill_id,
        players=1,
        needs=needs,
        level_min="beginner",
        level_max="advanced",
        duration_min=8,
        duration_max=12,
        skills=["dink"],
        target_metrics=NEW,
        review_status="coach-reviewed",
    )


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    copy = tmp_path / "drills"
    shutil.copytree(LIBRARY, copy)
    return {"path": copy}


def add(root: Path, doc: dict[str, Any]) -> None:
    folder = root / doc["id"]
    folder.mkdir()
    (folder / "v1.json").write_text(json.dumps(doc), encoding="utf-8")


@given("a drill library with no drill for AN-13 that 1 player can do at a wall")
def no_solo_wall_an13(ctx: dict[str, Any]) -> None:
    add(ctx["path"], pattern_drill("pb.test.court-patterns", ["half_court"]))
    add(ctx["path"], {**pattern_drill("pb.test.wall-an09", ["wall"]), "target_metrics": ["AN-09"]})


@given("a drill library with a solo wall drill and a solo court drill for AN-09 and AN-13")
def full_pattern_library(ctx: dict[str, Any]) -> None:
    add(ctx["path"], pattern_drill("pb.test.court-patterns", ["half_court"]))
    add(ctx["path"], pattern_drill("pb.test.wall-patterns", ["wall"]))


@when("the pattern coverage check runs")
def check_runs(ctx: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    ctx["rc"], ctx["out"] = run(capsys, ctx["path"], "--patterns")


@then(parsers.parse('it fails and names the cell "{cell}"'))
def fails_naming(ctx: dict[str, Any], cell: str) -> None:
    assert ctx["rc"] == 1, ctx["out"]
    assert f"FAIL {cell}" in fails(ctx["out"]), ctx["out"]
    assert all("× wall" in f and "AN-13" in f for f in fails(ctx["out"])), ctx["out"]


@then(parsers.parse("it passes with a fitting drill in all {n:d} pattern cells"))
def passes(ctx: dict[str, Any], n: int) -> None:
    assert ctx["rc"] == 0, ctx["out"]
    rows = [line for line in ctx["out"].splitlines() if line.startswith(("AN-09 ", "AN-13 "))]
    assert len(rows) == n, ctx["out"]
