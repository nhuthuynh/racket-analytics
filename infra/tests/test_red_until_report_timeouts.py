"""CI-REDUNTIL-HANG unit tests for scripts/ci/red_until_report.py.

Main run 37961668800: the red_until step ran 15 min and the job limit cancelled it. A row that
waits until pytest-timeout stops it did not fail for its story, and a run that stopped before
every collected row ran says nothing about the rows it skipped; both fail the report. A row
that fails for its story stays an expected red (W-01).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

SCRIPT = REPO_ROOT / "scripts" / "ci" / "red_until_report.py"
STORY = 'pytestmark = [pytest.mark.red_until(story="ST-052")]\n'
CLS = "tests.integration.test_it_03_11_full_tag"
RED = '<failure message="assert 404 == 201">RED until ST-052</failure>'
SIGNAL = '<failure message="Failed: Timeout (&gt;30.0s) from pytest-timeout.">dump</failure>'
THREAD = (
    '<error message="failed on setup with &quot;Failed: Timeout (&gt;120.0s) '
    'from pytest-timeout.&quot;"/>'
)


def _report(tmp: Path, cases: list[tuple[str, str]], *extra: str) -> subprocess.CompletedProcess:
    root = tmp / "backend"
    (root / "tests" / "integration").mkdir(parents=True, exist_ok=True)
    (root / "tests" / "integration" / "test_it_03_11_full_tag.py").write_text(STORY)
    body = "".join(f'<testcase classname="{CLS}" name="{n}">{i}</testcase>' for n, i in cases)
    xml = tmp / "red-until.xml"
    xml.write_text(f'<testsuites><testsuite name="pytest">{body}</testsuite></testsuites>')
    args = [sys.executable, str(SCRIPT), "--junit", str(xml), "--root", str(root), *extra]
    return subprocess.run(args, capture_output=True, text=True, check=False)


# ---------------------------------------------------------------- negative cases first
def test_a_row_stopped_by_pytest_timeout_fails_the_report(tmp_path: Path) -> None:
    res = _report(tmp_path, [("test_a", SIGNAL), ("test_b", RED)])
    assert res.returncode == 1, res.stdout + res.stderr
    assert "timed out" in res.stdout
    assert "test_a" in res.stdout


def test_a_timeout_in_setup_or_teardown_also_fails_the_report(tmp_path: Path) -> None:
    res = _report(tmp_path, [("test_a", THREAD)])
    assert res.returncode == 1, res.stdout + res.stderr
    assert "timed out" in res.stdout


def test_fewer_rows_than_collected_fails_the_report(tmp_path: Path) -> None:
    res = _report(tmp_path, [("test_a", RED)], "--expected-rows", "88")
    assert res.returncode == 1, res.stdout + res.stderr
    assert "1 of 88 rows ran" in res.stdout


def test_an_expected_row_count_that_is_not_a_positive_number_is_refused(tmp_path: Path) -> None:
    for bad in ("0", "-1", "x", ""):
        res = _report(tmp_path, [("test_a", RED)], "--expected-rows", bad)
        assert res.returncode == 2, (bad, res.stdout + res.stderr)


def test_the_summary_lists_the_timed_out_rows(tmp_path: Path) -> None:
    summary = tmp_path / "summary.md"
    res = _report(tmp_path, [("test_a", SIGNAL)], "--summary", str(summary))
    assert res.returncode == 1
    assert "timed out" in summary.read_text()


# ---------------------------------------------------------------- positive
def test_rows_that_fail_for_their_story_and_all_ran_pass(tmp_path: Path) -> None:
    res = _report(tmp_path, [("test_a", RED), ("test_b", RED)], "--expected-rows", "2")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "timed out" not in res.stdout


def test_a_failure_that_only_mentions_a_timeout_in_its_text_is_still_a_red(tmp_path: Path) -> None:
    """Only pytest-timeout's own message counts; a story's failure about a timeout is a red."""
    own = '<failure message="assert link_timeout_s == 900">RED until ST-052</failure>'
    res = _report(tmp_path, [("test_a", own)], "--expected-rows", "1")
    assert res.returncode == 0, res.stdout + res.stderr
