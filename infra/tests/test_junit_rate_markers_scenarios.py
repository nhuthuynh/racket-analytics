"""Binds tests/features/junit_rate_markers.feature (QA-VERIFY04R3-02-08): real pytest runs write
the JUnit reports and the real scripts/measure/junit_rate.py reads them, as the verifier does."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR
from domain_budget import run_in_backend
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("junit_rate_markers.feature")
JUNIT_RATE = SCRIPTS_DIR / "measure" / "junit_rate.py"
G04_11_A_INCLUDE = "test_it_04_|test_bola_matrix"  # goal-scorecard §4 G04-11 (a)
LIVE_VARIANT = "test_seed_demo_plan.py::test_it_04_11_live_stack_one_plan_and_a_rerun_keeps_its_id"


@dataclass
class Method:
    report: Path
    include: str = "."
    proc: subprocess.CompletedProcess[str] | None = None


def backend_report(tmp_path: Path, marker: str) -> Path:
    out = tmp_path / f"{marker}.xml"
    run = run_in_backend(
        [
            "uv",
            "run",
            "--no-sync",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-m",
            marker,
            f"--junitxml={out}",
            "tests/unit",
        ]
    )
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
    return out


def infra_report(tmp_path: Path, name: str) -> Path:
    out = tmp_path / f"{name}.xml"
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "no:xdist",
            f"--basetemp={tmp_path / ('bt-' + name)}",
            f"--deselect=tests/{LIVE_VARIANT}",
            f"--junitxml={out}",
            f"tests/{name}",
        ],
        cwd=REPO_ROOT / "infra",
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
    return out


def junit_rate(
    reports: list[Path], include: str, *require: str
) -> subprocess.CompletedProcess[str]:
    args = [a for r in require for a in ("--require", r)]
    return subprocess.run(
        [sys.executable, str(JUNIT_RATE), "--include", include, *args, *map(str, reports)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@given(
    parsers.parse('a JUnit report of the backend tests marked "{marker}"'), target_fixture="method"
)
def backend_marked(tmp_path: Path, marker: str) -> Method:
    return Method(backend_report(tmp_path, marker))


@given(
    parsers.parse('a JUnit report of the infra file "{name}" without its live-stack variant'),
    target_fixture="method",
)
def infra_file(tmp_path: Path, name: str) -> Method:
    return Method(infra_report(tmp_path, name), include=G04_11_A_INCLUDE)


@when(parsers.parse('the pass-rate method requires "{pattern}"'))
@when(parsers.parse('the G04-11 (a) method requires "{pattern}"'))
def require(method: Method, pattern: str) -> None:
    method.proc = junit_rate([method.report], method.include, pattern)


@then(parsers.parse('the method fails closed naming "{pattern}" as missing'))
def fails_closed(method: Method, pattern: str) -> None:
    assert method.proc is not None
    assert method.proc.returncode == 1, method.proc.stdout + method.proc.stderr
    assert json.loads(method.proc.stdout)["missing"] == [pattern]


@then("the method passes with every selected test passed")
def passes(method: Method) -> None:
    assert method.proc is not None
    result = json.loads(method.proc.stdout)
    assert method.proc.returncode == 0, method.proc.stdout + method.proc.stderr
    assert result["selected"] == result["passed"] > 0
    assert (result["failed"], result["skipped"], result["missing"]) == (0, 0, [])
