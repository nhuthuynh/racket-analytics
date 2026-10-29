"""CLI binding of tests/features/drill_coverage_solo_wall.feature (QA-VERIFY04R3-01; FR-124,
FR-141): ``racket-drill-coverage`` on a copy of ``content/drills`` left with one solo wall AN-04
drill (negative) and on ``content/drills``. Written red first."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.integration.test_it_04_13_drill_coverage_cli import LIBRARY, fails, run
from tests.integration.test_it_04_18_solo_wall_coverage import TARGETS, solo_wall_rows

scenarios("drill_coverage_solo_wall.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(
    parsers.parse("a drill library where {kept} is the only solo wall drill for {metric}"),
)
def one_solo_wall_drill(ctx: dict[str, Any], tmp_path: Path, kept: str, metric: str) -> None:
    copy = tmp_path / "drills"
    shutil.copytree(LIBRARY, copy)
    for path in sorted(p for p in copy.rglob("*.json") if p.name != "schema.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        solo_wall = doc["players"] == 1 and set(doc["needs"]) <= {"wall"}
        trains = "warm-up" not in doc["skills"] and metric in doc["target_metrics"]
        if solo_wall and trains and doc["id"] != kept:
            path.unlink()
    ctx["path"] = copy


@given("the starter drill library")
def starter_library(ctx: dict[str, Any]) -> None:
    ctx["path"] = LIBRARY


@when("the coverage check runs")
def check_runs(ctx: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    ctx["rc"], ctx["out"] = run(capsys, ctx["path"])


@then(parsers.parse('it fails and names the cell "{cell}"'))
def fails_naming(ctx: dict[str, Any], cell: str) -> None:
    assert ctx["rc"] == 1, ctx["out"]
    assert f"FAIL {cell}" in fails(ctx["out"]), ctx["out"]


@then("every target has at least 2 solo wall drills at intermediate")
def two_per_target(ctx: dict[str, Any]) -> None:
    assert ctx["rc"] == 0, ctx["out"]
    rows = solo_wall_rows(ctx["out"])
    assert sorted(rows) == sorted(TARGETS), ctx["out"]
    assert all(n >= 2 for n in rows.values()), rows
