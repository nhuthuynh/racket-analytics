"""Integration (FIX-03-2c, goal metric G03-12-PD-R1S3-01-PM): the checker run as a command on the
real checkout, and the scorecard's own method, `sed -n 35p docs/sprints/sprint-03.md`."""

from __future__ import annotations

import subprocess
import sys

import pytest
from conftest import REPO_ROOT
from unofficial_notice_fixtures import DICTIONARY, NEW_WORDS, PLAN, SCRIPT

pytestmark = pytest.mark.integration


def test_checker_refuses_a_file_without_the_rulebook_line(tmp_path) -> None:
    empty = tmp_path / "plan.md"
    empty.write_text("# nothing\n", encoding="utf-8")
    run = subprocess.run(
        [sys.executable, str(SCRIPT), str(empty), str(DICTIONARY)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert run.returncode == 2, run.stdout + run.stderr
    assert "Rulebook PDFs later" in run.stderr


def test_checker_passes_on_the_shipped_plan_and_dictionary() -> None:
    run = subprocess.run(
        [sys.executable, str(SCRIPT), str(PLAN), str(DICTIONARY)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert run.returncode == 0, run.stdout + run.stderr


def test_scorecard_method_line_35_carries_the_decided_words() -> None:
    run = subprocess.run(
        ["sed", "-n", "35p", "docs/sprints/sprint-03.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert "Rulebook PDFs later (OQ-01)" in run.stdout
    assert NEW_WORDS in run.stdout
    assert "every metric card" not in run.stdout
