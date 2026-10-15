"""Binds tests/features/demo_test_report_sprint03.feature (FIX-03-2d, goal metric DEMO-03):
the step 10 report run as the verifier runs it, on files written to a temporary directory."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR
from demo_report_fixtures import ledger, report_dir, scorecard
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("demo_test_report_sprint03.feature")

SCRIPT = SCRIPTS_DIR / "measure" / "demo_test_report.py"


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    return {"dir": tmp_path}


@given("a complete passing verifier report directory")
def reports(ctx: dict) -> None:
    ctx["reports"] = report_dir(ctx["dir"] / "reports")


@given(parsers.parse('the report "{name}" is missing'))
def missing(ctx: dict, name: str) -> None:
    (ctx["reports"] / name).unlink()


@given(parsers.parse('a ledger with an open blocker "{blocker}" and an open major "{major}"'))
def open_ledger(ctx: dict, blocker: str, major: str) -> None:
    ctx["ledger"] = ledger((blocker, "blocker"), (major, "major"))


@given("a ledger with no open blocker or major finding")
def closed_ledger(ctx: dict) -> None:
    ctx["ledger"] = ledger()


@given("a ledger without a review table")
def no_table(ctx: dict) -> None:
    ctx["ledger"] = "# Review rounds\n\nNothing yet.\n"


@given(parsers.parse('a scorecard whose latest totals are "{met:d} of {of:d} met"'))
def card(ctx: dict, met: int, of: int) -> None:
    ctx["scorecard"] = scorecard(met, of)


@when("the step 10 report runs")
def run(ctx: dict) -> None:
    args = [sys.executable, str(SCRIPT), "--reports", str(ctx["reports"])]
    for flag, name in (("--ledger", "review-rounds.md"), ("--scorecard", "goal-scorecard.md")):
        (ctx["dir"] / name).write_text(ctx[flag[2:]], encoding="utf-8")
        args += [flag, str(ctx["dir"] / name)]
    args += ["--json", str(ctx["dir"] / "out" / "step10.json")]
    ctx["proc"] = subprocess.run(args, capture_output=True, text=True, timeout=60, check=False)


@then(parsers.re(r"step 10 (?P<verdict>fails|passes)"))
def verdict(ctx: dict, verdict: str) -> None:
    assert ctx["proc"].returncode == (verdict == "fails"), ctx["proc"].stdout + ctx["proc"].stderr
    assert (ctx["dir"] / "out" / "step10.json").is_file()


@then("the step 10 report is refused as unreadable")
def refused(ctx: dict) -> None:
    assert ctx["proc"].returncode == 2, ctx["proc"].stdout + ctx["proc"].stderr
    assert "no review table" in ctx["proc"].stderr


@then(parsers.parse('it names "{text}"'))
def names(ctx: dict, text: str) -> None:
    assert text in ctx["proc"].stdout, ctx["proc"].stdout + ctx["proc"].stderr
