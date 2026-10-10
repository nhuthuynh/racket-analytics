"""Binds tests/features/reconcile_due.feature (FIX-03-1a, G03-12): the reconciliation check run
as the engineering-manager runs it, on real files."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from reconcile_ledger import ledger_section, plan, run_check

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("reconcile_due.feature")


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    return {"tmp": tmp_path, "ledger": "", "prs": [], "commits": [], "decisions": decisions}


@given(parsers.parse("a ledger with an open major row for {finding}"))
def open_row(ctx: dict, finding: str) -> None:
    ctx["ledger"] += ledger_section("Sprint close", [(finding, "major", "**Open.** not fixed")])


@given("a ledger without a review table")
def no_table(ctx: dict) -> None:
    ctx["ledger"] = "# Review rounds\n\nNothing here.\n"


@given(parsers.parse("a ledger whose section at main {sha} keeps {finding} open"))
def open_at_main(ctx: dict, sha: str, finding: str) -> None:
    ctx["ledger"] += ledger_section(
        f"Ticket DR-HELD-09 at `origin/main` `{sha}`", [(finding, "blocker", "Open, partly")]
    )


@given(parsers.parse("a later row that marks {finding} fixed by PR {pr}"))
def later_row(ctx: dict, finding: str, pr: str) -> None:
    ctx["ledger"] += ledger_section(
        "FIX: engineering-manager", [(finding, "major", f"**Fixed** on `main` by {pr}")]
    )


@given(
    parsers.parse(
        'a ticket plan where ticket {ticket} PR {pr} merged as {sha} carries a commit "{subject}"'
    )
)
def ticket_plan(ctx: dict, ticket: str, pr: str, sha: str, subject: str) -> None:
    ctx["prs"].append((ticket, pr, sha))
    ctx["commits"].append(("abc1234", subject, f"{ticket} ({pr})"))


@given(parsers.parse('a ticket decision file "{name}"'))
def decision_file(ctx: dict, name: str) -> None:
    (ctx["decisions"] / name).write_text("# decisions\n", encoding="utf-8")


@when("the reconciliation check runs")
def check(ctx: dict) -> None:
    ledger = ctx["tmp"] / "review-rounds.md"
    ledger.write_text(ctx["ledger"], encoding="utf-8")
    adr = ctx["tmp"] / "0039.md"
    adr.write_text(plan(ctx["prs"], ctx["commits"]), encoding="utf-8")
    ctx["out"] = run_check(ledger, adr, ctx["decisions"])


def _out(ctx: dict) -> subprocess.CompletedProcess[str]:
    return ctx["out"]


@then("the check fails")
def fails(ctx: dict) -> None:
    assert _out(ctx).returncode == 1, _out(ctx).stdout + _out(ctx).stderr


@then("the check fails with a usage error")
def fails_usage(ctx: dict) -> None:
    assert _out(ctx).returncode == 2, _out(ctx).stdout + _out(ctx).stderr
    assert _out(ctx).stderr.startswith("reconcile-due: "), _out(ctx).stderr


@then("the check passes")
def passes(ctx: dict) -> None:
    assert _out(ctx).returncode == 0, _out(ctx).stdout + _out(ctx).stderr


@then(parsers.parse("the report names {finding} as due because of ticket {ticket}"))
def names_due(ctx: dict, finding: str, ticket: str) -> None:
    due = [line for line in _out(ctx).stdout.splitlines() if line.startswith("due: ")]
    assert any(finding in line and f"ticket {ticket}" in line for line in due), _out(ctx).stdout


@then(parsers.parse("the report says {n:d} open row and {d:d} due"))
@then(parsers.parse("the report says {n:d} open rows and {d:d} due"))
def says_counts(ctx: dict, n: int, d: int) -> None:
    assert f"reconcile-due: {n} open blocker/major rows, {d} due" in _out(ctx).stdout
