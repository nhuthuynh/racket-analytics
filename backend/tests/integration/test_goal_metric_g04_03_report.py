"""FIX-04-2c (goal scorecard G04-03 a and c): a real ``pytest -m <marker> --junitxml`` run of the
coaching unit suites, read by ``scripts/measure/junit_rate.py --require-marker`` as §4 runs it.

Root cause of the red G04-03 row: ``--require weakness_golden`` is a regex over test ids
(``file|classname::name``) and a JUnit report carries no marker, so a passing golden run read as
``missing``. Each coaching test now records its marker names as the JUnit property ``markers``
and ``junit_rate.py`` requires a marker by exact name. Negative case first. Written red first.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tests.support.paths import BACKEND, REPO

JUNIT_RATE = REPO / "scripts" / "measure" / "junit_rate.py"
SUITES = ("tests/unit/coaching/test_weakness.py", "tests/unit/coaching/test_training_plan.py")
EXPECTED = {"weakness_golden": 9, "plan_property": 1}  # 7 catalogue comparisons + dict §2 A/B


def marker_run(marker: str, out: Path) -> Path:
    """Run the coaching unit suites selected by ``-m marker`` and return the JUnit report."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTEST_", "COV_CORE"))}
    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-m",
            marker,
            *SUITES,
            f"--junitxml={out}",
        ],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    assert res.returncode == 0, res.stdout[-2000:] + res.stderr[-2000:]
    return out


def rate(report: Path, *argv: str) -> tuple[int, dict[str, object]]:
    res = subprocess.run(
        [sys.executable, str(JUNIT_RATE), "--include", ".", *argv, str(report)],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert res.returncode in (0, 1), res.stderr
    return res.returncode, json.loads(res.stdout)


def case_markers(report: Path) -> list[set[str]]:
    found = []
    for case in ET.parse(report).getroot().iter("testcase"):  # noqa: S314 (our own report)
        props = {p.get("name"): p.get("value", "") for p in case.iter("property")}
        found.append(set(filter(None, props.get("markers", "").split(","))))
    return found


@pytest.fixture(scope="module")
def reports(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    base = tmp_path_factory.mktemp("g04-03")
    return {m: marker_run(m, base / f"{m}.xml") for m in EXPECTED}


def test_a_marker_no_test_carries_fails_closed_and_is_named(reports: dict[str, Path]) -> None:
    rc, result = rate(reports["weakness_golden"], "--require-marker", "plan_property")
    assert rc == 1
    assert result["missing"] == ["marker:plan_property"]
    assert result["ok"] is False


@pytest.mark.parametrize("marker", sorted(EXPECTED))
def test_every_selected_case_records_its_markers(reports: dict[str, Path], marker: str) -> None:
    markers = case_markers(reports[marker])
    assert len(markers) == EXPECTED[marker]
    assert all({marker, "unit"} <= m for m in markers), markers


@pytest.mark.parametrize("marker", sorted(EXPECTED))
def test_the_marker_run_meets_the_g04_03_method(reports: dict[str, Path], marker: str) -> None:
    rc, result = rate(reports[marker], "--require-marker", marker)
    assert rc == 0, result
    assert (result["selected"], result["passed"], result["skipped"], result["missing"]) == (
        EXPECTED[marker],
        EXPECTED[marker],
        0,
        [],
    )
