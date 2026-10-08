"""Binds tests/features/e2e_repeat_triage.feature (CI-FLAKE-RESUMABLE; NFR-074): the real
scripts/ci/e2e_repeat.sh and flaky_report.py; a stand-in `pnpm` checks the Playwright call, writes
the JUnit file of a `--repeat-each` run and exits 1 when any repeat failed, as Playwright does."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support.paths import REPO

scenarios("e2e_repeat_triage.feature")

SCRIPT = REPO / "scripts" / "ci" / "e2e_repeat.sh"
SPEC = "e2e/sprint-01/resumable-upload.spec.ts"
TITLE = "Resumable upload › Return after closing the tab"

FAKE_PNPM = r"""#!/usr/bin/env bash
set -euo pipefail
[[ "$1 $2 $3" == "exec playwright test" ]] || { echo "unexpected: $*" >&2; exit 97; }
shift 3
spec="$1"; shift
repeat=""
for a in "$@"; do case "$a" in --repeat-each=*) repeat="${a#--repeat-each=}" ;; esac; done
[[ "$*" != *--retries* ]] || exit 98
if [[ "$spec" != "$EXPECT_SPEC" || "$repeat" != "$EXPECT_REPEAT" || "$PW_PROJECTS" != chromium ]]
then
  echo "wrong call: spec=$spec repeat=$repeat project=$PW_PROJECTS" >&2
  exit 99
fi
case_open="<testcase classname=\"sprint-01/resumable-upload.spec.ts\" name=\"$FAKE_TITLE\""
{
  echo '<testsuites><testsuite name="sprint-01/resumable-upload.spec.ts">'
  for i in $(seq 1 "$repeat"); do
    if (( i <= FAKE_FAILS )); then
      echo "$case_open><failure message=\"banner not visible\"/></testcase>"
    else
      echo "$case_open/>"
    fi
  done
  echo '</testsuite></testsuites>'
} > "$PLAYWRIGHT_JUNIT_OUTPUT_NAME"
(( FAKE_FAILS == 0 ))
"""


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(parsers.parse("an E2E test that fails in {fails:d} of {total:d} repeats"))
def a_test(ctx: dict[str, Any], fails: int, total: int, tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pnpm = bin_dir / "pnpm"
    pnpm.write_text(FAKE_PNPM)
    pnpm.chmod(0o755)
    ctx.update(bin=bin_dir, fails=fails, total=total, reports=tmp_path / "reports")


@when(parsers.parse("the E2E repeat job runs it {repeat:d} times"))
def run_job(ctx: dict[str, Any], repeat: int) -> None:
    env = {
        "PATH": f"{ctx['bin']}{os.pathsep}{os.environ['PATH']}",
        "SPEC": SPEC,
        "GREP": "Return after closing the tab",
        "REPEAT": str(repeat),
        "PROJECT": "chromium",
        "REPORT_DIR": str(ctx["reports"]),
        "EXPECT_SPEC": SPEC,
        "EXPECT_REPEAT": str(repeat),
        "FAKE_FAILS": str(ctx["fails"]),
        "FAKE_TITLE": TITLE,
    }
    ctx["result"] = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO / "web",
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def _report(ctx: dict[str, Any]) -> str:
    report = ctx["reports"] / "e2e-repeat-flaky.md"
    assert report.is_file(), ctx["result"].stdout + ctx["result"].stderr
    return report.read_text()


@then("the job fails")
def job_fails(ctx: dict[str, Any]) -> None:
    res = ctx["result"]
    assert res.returncode not in (0, 2, 97, 98, 99), res.stdout + res.stderr


@then("the job passes")
def job_passes(ctx: dict[str, Any]) -> None:
    res = ctx["result"]
    assert res.returncode == 0, res.stdout + res.stderr


@then("the flaky report names the test as flaky")
def names_flaky(ctx: dict[str, Any]) -> None:
    report = _report(ctx)
    assert "1 flaky" in report
    assert TITLE in report


@then(parsers.parse('the flaky report says "{text}"'))
def report_says(ctx: dict[str, Any], text: str) -> None:
    assert text in _report(ctx)
