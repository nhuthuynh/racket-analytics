"""Binds tests/features/ci_reduntil_fail_fast.feature (CI-REDUNTIL-HANG; NFR-073, NFR-074):
the real report script on pytest-shaped JUnit files, and the real ci.yml."""

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
    (root / "tests" / "features").mkdir(parents=True, exist_ok=True)
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


def _report(run: dict[str, Any], *extra: str) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(SCRIPT), "--junit", str(run["xml"]), "--root", str(run["root"])]
    return subprocess.run([*args, *extra], capture_output=True, text=True, check=False)


@when("the red_until report reads the run", target_fixture="result")
def report(run: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    return _report(run, "--expected-rows", str(run["collected"]))


@then(parsers.re(r"the report (?P<verdict>fails|passes)$"))
def verdict(result: subprocess.CompletedProcess[str], verdict: str) -> None:
    assert result.returncode == {"fails": 1, "passes": 0}[verdict], result.stdout + result.stderr


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


@then(parsers.parse("the red_until step stops {what} after at most {limit:d} seconds"))
def bound(step: dict[str, Any], what: str, limit: int) -> None:
    option = {"a row": r"-o timeout=(\d+)\b", "the run": r"--session-timeout=(\d+)\b"}[what]
    found = re.search(option, step["run"])
    assert found is not None, step["run"]
    assert 0 < int(found.group(1)) <= limit, step["run"]


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


@then("the job keeps the whole object store log when it fails or is cancelled")
def store_log() -> None:
    steps = yaml.safe_load(CI.read_text())["jobs"]["integration"]["steps"]
    logs = next(s for s in steps if s.get("name", "").startswith("Service logs"))
    assert logs["if"].replace(" ", "") == "failure()||cancelled()", logs
    assert "logs --no-color objectstore > reports/objectstore.log" in logs["run"], logs
    upload = next(s for s in steps if s.get("with", {}).get("name") == "integration-reports")
    assert upload["with"]["path"] == "reports/"
    assert steps.index(logs) < steps.index(upload)


# ---------------------------------------------------------------- unit edge cases of the report
def test_a_timeout_in_setup_or_teardown_also_fails_the_report(tmp_path: Path) -> None:
    error = '<error message="failed on setup with &quot;Failed: Timeout (&gt;120.0s) from'
    res = _report(_run_file(tmp_path, [("t", error + ' pytest-timeout.&quot;"/>')], 1))
    assert res.returncode == 1, res.stdout + res.stderr
    assert "timed out" in res.stdout


def test_an_expected_row_count_that_is_not_a_positive_number_is_refused(tmp_path: Path) -> None:
    run = _run_file(tmp_path, [("test_a", RED)], 1)
    for bad in ("0", "-1", "x", ""):
        res = _report(run, "--expected-rows", bad)
        assert res.returncode == 2, (bad, res.stdout + res.stderr)


def test_the_summary_lists_the_timed_out_rows(tmp_path: Path) -> None:
    summary = tmp_path / "summary.md"
    res = _report(_run_file(tmp_path, [("t", TIMED_OUT)], 1), "--summary", str(summary))
    assert res.returncode == 1
    assert "timed out" in summary.read_text()


def test_a_failure_that_only_mentions_a_timeout_in_its_text_is_still_a_red(tmp_path: Path) -> None:
    """Only pytest-timeout's own message counts; a story's failure about a timeout is a red."""
    own = '<failure message="assert link_timeout_s == 900">RED until ST-051</failure>'
    res = _report(_run_file(tmp_path, [("test_a", own)], 1), "--expected-rows", "1")
    assert res.returncode == 0, res.stdout + res.stderr
