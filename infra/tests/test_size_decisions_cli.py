"""SIZE-WAIVERS-03 integration: the size_decisions.py CLI on the real decisions file.

Runs the script as the orchestrator does before a ticket PR opens: `check` the whole scope,
`apply` one PR's re-measured size. Real files, real subprocess.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR
from size_waivers_scope import DECISIONS, SCOPE

pytestmark = pytest.mark.integration
SCRIPT = SCRIPTS_DIR / "ci" / "size_decisions.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False
    )


def scope_args() -> list[str]:
    return [f"--scope={t}={n}" for t, n in SCOPE.items()]


# ---------------------------------------------------------------- negative cases first
def test_a_missing_decisions_file_fails_closed(tmp_path: Path) -> None:
    out = run("check", str(tmp_path / "absent.md"), *scope_args())
    assert out.returncode == 2, out.stdout + out.stderr


def test_a_decisions_file_missing_a_ticket_names_it(tmp_path: Path) -> None:
    text = DECISIONS.read_text()
    broken = tmp_path / "SIZE-WAIVERS-03.md"
    broken.write_text("\n".join(ln for ln in text.splitlines() if not ln.startswith("| ST-045 |")))
    out = run("check", str(broken), *scope_args())
    assert out.returncode == 1, out.stdout + out.stderr
    assert "ST-045: no size decision" in out.stdout


def test_a_waiver_at_the_measured_code_lines_alone_names_the_missing_room(tmp_path: Path) -> None:
    # SQA-1 (PR #6): the gate also counts the ticket's own decisions file.
    text = DECISIONS.read_text()
    short = tmp_path / "SIZE-WAIVERS-03.md"
    short.write_text(text.replace("| ST-050 | 412 | waived 452 |", "| ST-050 | 412 | waived 412 |"))
    out = run("check", str(short), *scope_args())
    assert out.returncode == 1, out.stdout + out.stderr
    assert "ST-050: the PRs cover 412 of 452 changed lines" in out.stdout


def test_apply_above_a_waiver_asks_for_a_new_row() -> None:
    out = run("apply", str(DECISIONS), "--ticket=ST-050", "--pr=1", "--changed=453")
    assert out.returncode == 1, out.stdout + out.stderr
    assert "new decision row needed" in out.stdout


# ---------------------------------------------------------------- positive
def test_the_real_decisions_file_covers_the_whole_scope() -> None:
    out = run("check", str(DECISIONS), *scope_args())
    assert out.returncode == 0, out.stdout + out.stderr
    assert f"size-decisions: {len(SCOPE)} tickets decided" in out.stdout


def test_apply_prints_the_label_to_put_on_the_pr() -> None:
    waived = run("apply", str(DECISIONS), "--ticket=ST-050", "--pr=1", "--changed=452")
    stacked = run("apply", str(DECISIONS), "--ticket=ST-050b", "--pr=1", "--changed=399")
    assert (waived.returncode, waived.stdout.splitlines()[0]) == (0, "label: size-waiver")
    assert (stacked.returncode, stacked.stdout.splitlines()[0]) == (0, "label: none")
