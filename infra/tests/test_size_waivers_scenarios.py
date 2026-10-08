"""Binds tests/features/size_waivers.feature (SIZE-WAIVERS-03; NFR-077).

The real decisions file, real git, and the `PR size` step of ci.yml run verbatim on the merge
ref, with the label the size decision gives (pr_checkout.py builds the PR).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR
from pr_checkout import GIT_ENV, SIZE_STEP, PullRequest, lines, policy_steps
from pytest_bdd import given, parsers, scenarios, then, when
from size_waivers_scope import DECISIONS, SCOPE

pytestmark = pytest.mark.integration
scenarios("size_waivers.feature")
SCRIPT = SCRIPTS_DIR / "ci" / "size_decisions.py"


def size_decisions(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False
    )


@given(parsers.parse('the size decision for "{ticket}" PR {pr:d}'), target_fixture="ticket_pr")
def ticket_pr(ticket: str, pr: int) -> tuple[str, int]:
    return ticket, pr


@given(parsers.parse("that PR changes {n:d} lines"), target_fixture="pr")
def pr_changes(tmp_path: Path, n: int) -> tuple[PullRequest, int]:
    pr = PullRequest.opened_against_main(tmp_path)
    pr.open_event("backend/src/change.py", lines(n))
    return pr, n


@given(
    parsers.parse("that PR changes {n:d} code lines and adds its own {d:d}-line decisions file"),
    target_fixture="pr",
)
def pr_changes_with_decisions_file(tmp_path: Path, n: int, d: int) -> tuple[PullRequest, int]:
    # SQA-1 (PR #6): the gate counts docs/sprints/03/decisions/<ID>.md (PO rule 2026-10-07).
    pr = PullRequest.opened_against_main(tmp_path)
    pr.push("pr", "docs/sprints/03/decisions/HARNESS-03.md", lines(d))
    pr.open_event("backend/src/change.py", lines(n))
    return pr, n + d


@when(
    "the size decision is applied and the PR policy checks run on the merge ref",
    target_fixture="outcome",
)
def apply_and_run(ticket_pr: tuple[str, int], pr: tuple[PullRequest, int]) -> dict:
    (ticket, k), (request, n) = ticket_pr, pr
    decision = size_decisions(
        "apply", str(DECISIONS), f"--ticket={ticket}", f"--pr={k}", f"--changed={n}"
    )
    labels = ["size-waiver"] if decision.stdout.startswith("label: size-waiver") else []
    request.checkout_merge_ref()
    step = next(s for s in policy_steps() if s["name"] == SIZE_STEP)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")} | GIT_ENV
    env |= {"PR_LABELS": json.dumps(labels), "BASE_REF": "main"}
    gate = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=request.runner,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )
    return {"decision": decision, "labels": labels, "gate": gate}


@then("the decision asks for a new decision row")
def new_row(outcome: dict) -> None:
    assert outcome["decision"].returncode == 1, outcome["decision"].stdout
    assert "new decision row needed" in outcome["decision"].stdout


@then("no size-waiver label is applied")
def no_label(outcome: dict) -> None:
    assert outcome["labels"] == []


@then("the size-waiver label is applied")
def label(outcome: dict) -> None:
    assert outcome["decision"].returncode == 0, outcome["decision"].stdout
    assert outcome["labels"] == ["size-waiver"]


@then(parsers.parse("the PR size check {verdict} and counts {n:d} changed lines"))
def size_verdict(outcome: dict, verdict: str, n: int) -> None:
    out = outcome["gate"]
    assert out.returncode == {"passes": 0, "fails": 1}[verdict], out.stdout
    assert f"pr-size: {n} changed lines" in out.stdout


@given("the Sprint 3 ticket PRs measured over 400 changed lines", target_fixture="scope")
def scope() -> dict[str, int]:
    return SCOPE


@when("the SIZE-WAIVERS-03 decisions file is checked against them", target_fixture="check")
def check(scope: dict[str, int]) -> subprocess.CompletedProcess[str]:
    return size_decisions("check", str(DECISIONS), *(f"--scope={t}={n}" for t, n in scope.items()))


@then("every ticket has a size decision")
def every_ticket(check: subprocess.CompletedProcess[str]) -> None:
    assert check.returncode == 0, check.stdout + check.stderr
    assert "no size decision" not in check.stdout


@then("no stacked part without a waiver is over 400 changed lines")
def no_oversize_part(check: subprocess.CompletedProcess[str]) -> None:
    assert "without a waiver" not in check.stdout


@then("every ticket's PRs leave room for its own decisions file")
def room_for_decisions_file(check: subprocess.CompletedProcess[str]) -> None:
    assert "for its decisions file" not in check.stdout
