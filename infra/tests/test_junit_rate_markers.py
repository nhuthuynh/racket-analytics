"""QA-VERIFY04R3-02-08: the goal-scorecard methods of G04-03 (a)/(c) and G04-11 (a), run as written.

VERIFY-04-r3 found `junit_rate.py --require weakness_golden` rc 1 `missing` while the 9 golden
tests passed (a JUnit report names tests, not markers), and `--require test_it_04_11/15` rc 1
while IT-04-11 and IT-04-15 passed under other names. Each pytest run now records its markers as
the `markers` property of the test case; the two IT files name their tests `test_it_04_nn_*`.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from domain_budget import run_in_backend
from test_junit_rate_markers_scenarios import (
    G04_11_A_INCLUDE,
    backend_report,
    infra_report,
    junit_rate,
)

pytestmark = pytest.mark.integration


def markers_of(report: Path) -> dict[str, set[str]]:
    root = ET.parse(report).getroot()  # noqa: S314 - the report our own pytest run wrote
    return {
        f"{case.get('classname')}::{case.get('name')}": set(
            next(
                (p.get("value", "") for p in case.iter("property") if p.get("name") == "markers"),
                "",
            ).split()
        )
        for case in root.iter("testcase")
    }


def test_a_backend_run_on_xdist_workers_records_each_tests_markers(tmp_path: Path) -> None:
    out = tmp_path / "golden.xml"
    run = run_in_backend(
        [
            "uv",
            "run",
            "--no-sync",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-n",
            "2",
            "-m",
            "weakness_golden",
            f"--junitxml={out}",
            "tests/unit",
        ]
    )
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
    cases = markers_of(out)
    assert len(cases) >= 9, cases  # 9 golden/catalogue comparisons (G04-03 a)
    assert all({"unit", "weakness_golden"} <= names for names in cases.values()), cases


def test_g04_03_method_finds_the_golden_marker(tmp_path: Path) -> None:
    proc = junit_rate([backend_report(tmp_path, "weakness_golden")], ".", "weakness_golden")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_an_infra_run_records_markers_too(tmp_path: Path) -> None:
    cases = markers_of(infra_report(tmp_path, "test_check_red_first.py"))
    assert cases
    assert all("integration" in names for names in cases.values()), cases


def test_g04_11_a_method_finds_it_04_11_and_it_04_15_together(tmp_path: Path) -> None:
    reports = [
        infra_report(tmp_path, n) for n in ("test_seed_demo_plan.py", "test_check_red_first.py")
    ]
    proc = junit_rate(reports, G04_11_A_INCLUDE, "test_it_04_11", "test_it_04_15")
    assert proc.returncode == 0, proc.stdout + proc.stderr
