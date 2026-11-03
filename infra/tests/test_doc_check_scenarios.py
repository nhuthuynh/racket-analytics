"""Binds tests/features/doc_check.feature (CI-DOC-CHECK): scripts/ci/check_docs.py run as a
process, as the ci.yml doc-check job runs it, on a clone of the real repository (real register,
real agent files, real check_flows.py) with one planted break per scenario."""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from doc_check_repo import commit, flows_text, git, run_check, write
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("doc_check.feature")


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    return {"root": tmp_path / "clone"}


@given("a clone of the repository at its current commit")
def clone(ctx: dict) -> None:
    subprocess.run(["git", "clone", "-q", "--shared", str(REPO_ROOT), str(ctx["root"])], check=True)
    ctx["base"] = git(ctx["root"], "rev-parse", "HEAD")


@given(parsers.parse('a changed Markdown file that names "{path}"'))
def names_path(ctx: dict, path: str) -> None:
    write(ctx["root"], "docs/planted-doc-check.md", f"# Planted\n\nRun `{path}`.\n")
    commit(ctx["root"])


@given(parsers.parse('a changed Markdown file that cites "{citation}"'))
def cites(ctx: dict, citation: str) -> None:
    write(ctx["root"], "docs/planted-doc-check.md", f"# Planted\n\nA claim {citation}.\n")
    commit(ctx["root"])


@given(parsers.parse('the agent file "{role}" without its tools line'))
def agent_without_tools(ctx: dict, role: str) -> None:
    path = ctx["root"] / ".claude" / "agents" / f"{role}.md"
    path.write_text(re.sub(r"^tools:.*\n", "", path.read_text(), count=1, flags=re.M))
    commit(ctx["root"])


@given("the current sprint's flows file with a pending decider cell")
def pending_flows(ctx: dict) -> None:
    plans = sorted((ctx["root"] / "docs" / "sprints").glob("sprint-[0-9][0-9].md"))
    sprint = plans[-1].stem.split("-")[1]
    write(ctx["root"], f"docs/design/flows-sprint-{sprint}.md", flows_text("pending", sprint))
    commit(ctx["root"])


@given(parsers.parse('every agent file gains a line citing "{citation}" and naming "{path}"'))
def every_agent(ctx: dict, citation: str, path: str) -> None:
    agents = sorted((ctx["root"] / ".claude" / "agents").glob("*.md"))
    assert len(agents) >= 12, agents
    for agent in agents:
        agent.write_text(agent.read_text() + f"\nSee `{path}` {citation}.\n")
    commit(ctx["root"])


@when("doc-check runs on the change")
def run(ctx: dict) -> None:
    start = time.monotonic()
    ctx["proc"] = run_check(ctx["root"], "--base", ctx["base"], "--head", "HEAD")
    ctx["seconds"] = time.monotonic() - start


@then(parsers.parse('doc-check exits {rc:d} with "{text}"'))
def exits(ctx: dict, rc: int, text: str) -> None:
    out = ctx["proc"].stdout + ctx["proc"].stderr
    assert ctx["proc"].returncode == rc, out
    assert text in out, out


@then(parsers.parse("doc-check took less than {seconds:d} seconds"))
def took(ctx: dict, seconds: int) -> None:
    assert ctx["seconds"] < seconds, ctx["seconds"]
