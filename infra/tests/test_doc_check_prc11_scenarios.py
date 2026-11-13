"""Binds tests/features/doc_check_prc11.feature (CI-DOC-CHECK-06, PRC-11.1-11.3): check_docs.py
and check_cost_table.py run as processes, as ci.yml runs them, on a clone of the real repository
(real sources register, real threat notes and their checker, real decisions files) with one planted
case per scenario."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from doc_check_prc11 import COST_TABLE, reference, run_cost
from doc_check_repo import commit, git, run_check, write
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("doc_check_prc11.feature")


def current_sprint(root: Path) -> str:
    plans = sorted((root / "docs" / "sprints").glob("sprint-[0-9][0-9].md"))
    return plans[-1].stem.split("-")[1]


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    return {"root": tmp_path / "clone"}


@given("a clone of the repository at its current commit")
def clone(ctx: dict) -> None:
    subprocess.run(["git", "clone", "-q", "--shared", str(REPO_ROOT), str(ctx["root"])], check=True)
    ctx["base"] = git(ctx["root"], "rev-parse", "HEAD")


@given(parsers.parse('a reference set file whose entry cites "{cid}"'))
def reference_file(ctx: dict, cid: str) -> None:
    write(ctx["root"], "content/references/planted-doc-check/v1.json", reference(cid))
    commit(ctx["root"])


@given("the newest threat notes gain a threat row with an empty status cell")
def broken_notes(ctx: dict) -> None:
    notes = sorted((ctx["root"] / "docs" / "security").glob("threat-notes-sprint-[0-9][0-9].md"))
    n = int(notes[-1].stem.rsplit("-", 1)[1])
    row = f"| T{n}-ZZ-9 | S | planted | planted | V2 | PLANTED | IT-planted | |"
    notes[-1].write_text(notes[-1].read_text() + f"\n{row}\n")
    commit(ctx["root"])


@given("a changed Markdown file with no references")
def plain(ctx: dict) -> None:
    write(ctx["root"], "docs/planted-doc-check.md", "# Planted\n\nPlain text.\n")
    commit(ctx["root"])


@given(parsers.parse('the decisions file of ticket "{ticket}" without a cost per PR table'))
def no_cost(ctx: dict, ticket: str) -> None:
    rel = f"docs/sprints/{current_sprint(ctx['root'])}/decisions/{ticket}.md"
    write(ctx["root"], rel, f"# {ticket} decisions\n\n## 1. Size\n\nS.\n")
    commit(ctx["root"])


@given(parsers.parse('the decisions file of ticket "{ticket}" with a cost per PR row'))
def with_cost(ctx: dict, ticket: str) -> None:
    rel = f"docs/sprints/{current_sprint(ctx['root'])}/decisions/{ticket}.md"
    write(ctx["root"], rel, f"# {ticket} decisions\n\n{COST_TABLE}")
    commit(ctx["root"])


@when("doc-check runs on the change")
def run(ctx: dict) -> None:
    ctx["proc"] = run_check(ctx["root"], "--base", ctx["base"], "--head", "HEAD")


@when(parsers.parse('the cost-table check runs for the PR title "{title}"'))
def run_cost_check(ctx: dict, title: str) -> None:
    ctx["proc"] = run_cost(ctx["root"], "--title", title)


@then(parsers.parse('doc-check exits {rc:d} with "{text}"'))
@then(parsers.parse('the cost-table check exits {rc:d} with "{text}"'))
def exits(ctx: dict, rc: int, text: str) -> None:
    out = ctx["proc"].stdout + ctx["proc"].stderr
    assert ctx["proc"].returncode == rc, out
    assert re.search(re.escape(text), out), out
