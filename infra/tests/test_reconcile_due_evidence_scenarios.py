"""Binds tests/features/reconcile_due_evidence.feature (C4-RECON, VM-R3-02): the reconciliation
check run against a real git ``main`` whose ticket PRs are merged the way GitHub merges them."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from reconcile_evidence import (
    DECISIONS,
    LEDGER,
    append_ledger,
    evidence_section,
    init_main,
    merge_ticket,
    open_row,
)
from reconcile_ledger import run_check

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("reconcile_due_evidence.feature")


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    return {"repo": tmp_path, "ledger": "", "files": [], "started": False}


def _main(ctx: dict) -> Path:
    if not ctx["started"]:
        init_main(ctx["repo"], ctx["ledger"], ctx["files"])
        ctx["started"] = True
    return ctx["repo"]


@given(
    parsers.parse('a ledger with an open major row for {finding} whose evidence cites "{cited}"')
)
def ledger_with_open_row(ctx: dict, finding: str, cited: str) -> None:
    ctx["ledger"] += open_row(finding, cited)
    ctx["files"].append(cited)


@given(parsers.parse("a verifier row {finding} that is open and major"))
def verifier_row(ctx: dict, finding: str) -> None:
    ctx["ledger"] += evidence_section(
        "VERIFY-99-r1", [(finding, "major", "**Open.** found on main", "scorecard §1")]
    )


@given(parsers.parse('ticket {ticket} is merged as PR #{pr:d} and changes "{changed}"'))
def merged_ticket(ctx: dict, ticket: str, pr: int, changed: str) -> None:
    merge_ticket(_main(ctx), ticket, pr, [changed])


@given(parsers.parse('ticket {ticket} is merged as PR #{pr:d} with the title "{title}"'))
def merged_ticket_titled(ctx: dict, ticket: str, pr: int, title: str) -> None:
    merge_ticket(_main(ctx), ticket, pr, ["docs/other.md"], title=title)


@given(parsers.parse("the engineering-manager then writes a later row that keeps {finding} open"))
def later_row(ctx: dict, finding: str) -> None:
    append_ledger(
        _main(ctx),
        evidence_section(
            "EM status",
            [(finding, "major", "**Open.** re-checked", "`sed -n 3p docs/design/flows.md`")],
        ),
    )


@when("the reconciliation check runs against main")
def check(ctx: dict) -> None:
    repo = _main(ctx)
    ctx["out"] = run_check(repo / LEDGER, None, repo / DECISIONS, "main")


@when("the reconciliation check runs against main in report-only mode")
def check_report_only(ctx: dict) -> None:
    repo = _main(ctx)
    ctx["out"] = run_check(repo / LEDGER, None, repo / DECISIONS, "main", report_only=True)


@then("the check fails")
def fails(ctx: dict) -> None:
    assert ctx["out"].returncode == 1, ctx["out"].stdout + ctx["out"].stderr


@then("the check passes")
def passes(ctx: dict) -> None:
    assert ctx["out"].returncode == 0, ctx["out"].stdout + ctx["out"].stderr


@then(parsers.parse("the report names {finding} as due because of ticket {ticket} ({pr})"))
def names_due(ctx: dict, finding: str, ticket: str, pr: str) -> None:
    due = [line for line in ctx["out"].stdout.splitlines() if line.startswith("due: ")]
    assert any(
        finding in line and f"ticket {ticket} ({pr})" in line and "evidence" in line for line in due
    ), ctx["out"].stdout


@then(
    parsers.parse(
        "the report names {finding} as due because the title of ticket {ticket} ({pr}) names it"
    )
)
def names_due_by_title(ctx: dict, finding: str, ticket: str, pr: str) -> None:
    due = [line for line in ctx["out"].stdout.splitlines() if line.startswith("due: ")]
    assert any(
        finding in line and f"named by the PR title of ticket {ticket} ({pr})" in line
        for line in due
    ), ctx["out"].stdout


@then(parsers.parse("the report says {n:d} open row and {d:d} due"))
@then(parsers.parse("the report says {n:d} open rows and {d:d} due"))
def says_counts(ctx: dict, n: int, d: int) -> None:
    out = ctx["out"]
    assert f"reconcile-due: {n} open blocker/major rows, {d} due" in out.stdout, (
        out.stdout + out.stderr
    )
