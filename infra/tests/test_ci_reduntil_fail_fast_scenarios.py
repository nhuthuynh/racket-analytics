"""Binds tests/features/ci_reduntil_fail_fast.feature (CI-REDUNTIL-HANG; NFR-073, NFR-074).

The real report script on JUnit files shaped like pytest's, and the real ci.yml. The real-store
path (a row waiting on a slow object store) is backend/tests/integration/harness/
test_ci_reduntil_step_bound.py.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO_ROOT
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.unit
scenarios("ci_reduntil_fail_fast.feature")

SCRIPT = REPO_ROOT / "scripts" / "ci" / "red_until_report.py"
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
STORY_FILE = 'pytestmark = [pytest.mark.red_until(story="ST-051")]\n'
CLS = "tests.features.test_account_deletion"
RED = '<failure message="assert 404 == 204">RED until ST-051</failure>'
TIMED_OUT = (
    '<failure message="Failed: Timeout (&gt;30.0s) from pytest-timeout.">+++ Timeout</failure>'
)


def _run_file(tmp: Path, cases: list[tuple[str, str]], collected: int) -> dict[str, Any]:
    root = tmp / "backend"
    (root / "tests" / "features").mkdir(parents=True)
    (root / "tests" / "features" / "test_account_deletion.py").write_text(STORY_FILE)
    body = "".join(
        f'<testcase classname="{CLS}" name="{n}">{inner}</testcase>' for n, inner in cases
    )
    xml = tmp / "red-until.xml"
    xml.write_text(f'<testsuites><testsuite name="pytest">{body}</testsuite></testsuites>')
    return {"root": root, "xml": xml, "collected": collected}


@given(
    "a red_until run in which one row failed for its story and one row timed out",
    target_fixture="run",
)
def one_timed_out(tmp_path: Path) -> dict[str, Any]:
    return _run_file(
        tmp_path, [("test_delete_account", TIMED_OUT), ("test_signing_in_again", RED)], 2
    )


@given(
    parsers.parse("a red_until run that collected {collected:d} rows and reported {reported:d}"),
    target_fixture="run",
)
@given(
    parsers.parse(
        "a red_until run that collected {collected:d} rows and reported {reported:d} "
        "that failed for their story"
    ),
    target_fixture="run",
)
def red_rows(tmp_path: Path, collected: int, reported: int) -> dict[str, Any]:
    """``reported`` rows that failed for their story, out of ``collected``."""
    return _run_file(tmp_path, [(f"test_row_{i}", RED) for i in range(reported)], collected)


@when("the red_until report reads the run", target_fixture="result")
def report(run: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(SCRIPT), "--junit", str(run["xml"]), "--root", str(run["root"])]
    args += ["--expected-rows", str(run["collected"])]
    return subprocess.run(args, capture_output=True, text=True, check=False)


@then("the report fails")
def fails(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 1, result.stdout + result.stderr


@then("the report passes")
def passes(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr


@then("the report names the timed-out row")
def names_row(result: subprocess.CompletedProcess[str]) -> None:
    line = next((x for x in result.stdout.splitlines() if "timed out" in x), "")
    assert "test_delete_account" in line, result.stdout
    assert "test_signing_in_again" not in line


@then(parsers.parse("the report says that {ran:d} of {collected:d} rows ran"))
def says_count(result: subprocess.CompletedProcess[str], ran: int, collected: int) -> None:
    assert f"{ran} of {collected} rows ran" in result.stdout, result.stdout


# ---------------------------------------------------------------- the CI step
@given("the CI workflow", target_fixture="step")
def step() -> dict[str, Any]:
    steps = yaml.safe_load(CI.read_text())["jobs"]["integration"]["steps"]
    return next(s for s in steps if "red_until" in s.get("name", ""))


def _option(step: dict[str, Any], pattern: str) -> int | None:
    found = re.search(pattern, step["run"])
    return int(found.group(1)) if found else None


@then(parsers.parse("the red_until step stops a row after at most {limit:d} seconds"))
def per_row(step: dict[str, Any], limit: int) -> None:
    seconds = _option(step, r"-o timeout=(\d+)\b")
    assert seconds is not None, step["run"]
    assert 0 < seconds <= limit, step["run"]


@then(parsers.parse("the red_until step stops the run after at most {limit:d} seconds"))
def whole_run(step: dict[str, Any], limit: int) -> None:
    seconds = _option(step, r"--session-timeout=(\d+)\b")
    assert seconds is not None, step["run"]
    assert 0 < seconds <= limit, step["run"]


@then("the red_until step gives the report the number of rows it collected")
def collected(step: dict[str, Any]) -> None:
    run = step["run"]
    assert "--collect-only" in run, run
    assert re.search(r"red_until_report\.py[^\n]*\\?\s*[^\n]*--expected-rows \"\$\w+\"", run), run


@then(parsers.parse("the red_until step has its own time limit of at most {limit:d} minutes"))
def own_limit(step: dict[str, Any], limit: int) -> None:
    minutes = step.get("timeout-minutes")
    assert isinstance(minutes, int), step
    assert 0 < minutes <= limit, step
