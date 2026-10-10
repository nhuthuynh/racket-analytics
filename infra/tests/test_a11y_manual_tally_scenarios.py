"""Binds tests/features/a11y_manual_tally.feature (FIX-03-1b, S3-DoD-P6): the tally script run
as the reporter runs it, on manual files written to a temporary directory."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from a11y_manual_fixtures import manual, sprint_plan
from conftest import SCRIPTS_DIR
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("a11y_manual_tally.feature")

SCRIPT = SCRIPTS_DIR / "measure" / "a11y_manual.py"


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    return {"dir": tmp_path}


def _write(ctx: dict, text: str) -> None:
    ctx["manual"] = ctx["dir"] / "a11y-manual.md"
    ctx["manual"].write_text(text, encoding="utf-8")


@given("a manual with no result table")
def no_table(ctx: dict) -> None:
    _write(ctx, "# Manual\n\n## 3. Script and results\n\nNothing yet.\n\n## 4. Result\n")


@given("a manual with rows 1 to 3 and 5")
def gap(ctx: dict) -> None:
    _write(ctx, manual(4, ids=["1", "2", "3", "5"]))


@given("a manual of 38 rows with no result recorded")
def none_run(ctx: dict) -> None:
    _write(ctx, manual(38))


@given("a manual of 38 rows with every VoiceOver result recorded and 37 TalkBack results")
def one_missing(ctx: dict) -> None:
    _write(ctx, manual(38, voiceover=38, talkback=37))


@given("a manual of 38 rows with every result recorded on both screen readers")
def all_run(ctx: dict) -> None:
    _write(ctx, manual(38, voiceover=38, talkback=38))


@given(parsers.parse('a sprint plan whose S3-DoD-P6 row says "{status}"'))
def plan(ctx: dict, status: str) -> None:
    ctx["plan"] = ctx["dir"] / "sprint-03.md"
    ctx["plan"].write_text(sprint_plan(status), encoding="utf-8")


def _run(*args: Path | str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True, timeout=60
    )


@when("the manual is tallied")
def tally(ctx: dict) -> None:
    ctx["out"] = _run(ctx["manual"])


@when("the manual is tallied against the sprint plan")
def tally_plan(ctx: dict) -> None:
    ctx["out"] = _run(ctx["manual"], "--dod", ctx["plan"])


@then("the tally is refused as malformed")
def malformed(ctx: dict) -> None:
    out = ctx["out"]
    assert out.returncode == 2, out.stdout + out.stderr
    assert "a11y_manual:" in out.stderr


@then(parsers.parse('the status is "{status}"'))
def status_is(ctx: dict, status: str) -> None:
    out = ctx["out"]
    assert out.returncode == (0 if status.startswith("met") else 1), out.stdout + out.stderr
    assert json.loads(out.stdout)["status"] == status


@then("the tally reports that the sprint-DoD row disagrees with the manual")
def disagrees(ctx: dict) -> None:
    out = ctx["out"]
    assert out.returncode == 3, out.stdout + out.stderr
    assert "S3-DoD-P6" in out.stderr
    assert "not met: waiting on P6 (0 of 38 rows run)" in out.stderr
