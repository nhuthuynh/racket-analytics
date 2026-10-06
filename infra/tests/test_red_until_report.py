"""W-01 (CI run 37434214390): rows marked ``red_until(story=…)`` are listed, not gated.

sprint-02 §8: "every row of a committed story green; rows `red_until` a stretch story listed
separately". The per-PR integration gate therefore selects ``not red_until``; this report runs on
the red-until rows alone. It fails closed in two ways: a red-until row that **passes** is a stale
marker (retro 1 A2) and fails the job, and so does a run that selected nothing or a row whose
file names no story.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

SCRIPT = REPO_ROOT / "scripts" / "ci" / "red_until_report.py"


def tree(tmp: Path, files: dict[str, str]) -> Path:
    root = tmp / "backend"
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    return root


def junit(tmp: Path, cases: list[tuple[str, str, str]]) -> Path:
    """cases: (classname, name, outcome) with outcome passed | failed | skipped | error."""
    body = []
    for cls, name, outcome in cases:
        inner = {
            "passed": "",
            "failed": '<failure message="RED until ST-035: seam"/>',
            "skipped": '<skipped message="P3"/>',
            "error": '<error message="boom"/>',
        }[outcome]
        body.append(f'<testcase classname="{cls}" name="{name}">{inner}</testcase>')
    xml = tmp / "red-until.xml"
    xml.write_text(f'<testsuites><testsuite name="pytest">{"".join(body)}</testsuite></testsuites>')
    return xml


SOS = 'pytestmark = [pytest.mark.red_until(story="ST-035"), pytest.mark.scoring]\n'
NIGHTLY = 'pytestmark = pytest.mark.red_until(story="ST-024")\n'


def run(xml: Path, root: Path, summary: Path | None = None) -> subprocess.CompletedProcess:
    args = [sys.executable, str(SCRIPT), "--junit", str(xml), "--root", str(root)]
    if summary:
        args += ["--summary", str(summary)]
    return subprocess.run(args, capture_output=True, text=True, check=False)


# ---------------------------------------------------------------- negative cases first
def test_missing_junit_fails_closed(tmp_path: Path) -> None:
    res = run(tmp_path / "none.xml", tree(tmp_path, {}))
    assert res.returncode == 2, res


def test_an_empty_selection_fails_closed(tmp_path: Path) -> None:
    res = run(junit(tmp_path, []), tree(tmp_path, {}))
    assert res.returncode == 1
    assert "no red_until rows" in res.stdout + res.stderr


def test_a_red_until_row_that_passes_is_a_stale_marker(tmp_path: Path) -> None:
    root = tree(tmp_path, {"tests/features/test_side_out_singles_provisional.py": SOS})
    xml = junit(
        tmp_path,
        [("tests.features.test_side_out_singles_provisional", "test_sos01", "passed")],
    )
    res = run(xml, root)
    assert res.returncode == 1
    assert "stale" in res.stdout
    assert "ST-035" in res.stdout


def test_a_row_whose_file_names_no_story_fails(tmp_path: Path) -> None:
    root = tree(tmp_path, {"tests/features/test_x.py": "import pytest\n"})
    res = run(junit(tmp_path, [("tests.features.test_x", "test_a", "failed")]), root)
    assert res.returncode == 1
    assert "no story" in res.stdout


# ---------------------------------------------------------------- positive
def test_failing_red_until_rows_are_listed_per_story_and_do_not_fail(tmp_path: Path) -> None:
    root = tree(
        tmp_path,
        {
            "tests/features/test_side_out_singles_provisional.py": SOS,
            "tests/features/test_nightly_quality.py": NIGHTLY,
        },
    )
    xml = junit(
        tmp_path,
        [
            ("tests.features.test_side_out_singles_provisional", "test_sos01", "failed"),
            ("tests.features.test_side_out_singles_provisional", "test_sos02", "failed"),
            ("tests.features.test_nightly_quality", "test_nightly_run_completes", "failed"),
        ],
    )
    summary = tmp_path / "summary.md"
    res = run(xml, root, summary)
    assert res.returncode == 0, res.stdout + res.stderr
    text = summary.read_text()
    assert "| ST-035 | 2 | 0 |" in text
    assert "| ST-024 | 1 | 0 |" in text
    assert "not gated" in text.lower()
