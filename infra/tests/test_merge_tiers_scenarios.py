"""Binds tests/features/merge_tiers.feature (CI-TIERS-b; PRC-2.4-2.7): the merge check run as
the merge step runs it, over HTTP against the local GitHub API stub, which serves the PR's
files and `docs/sprints/<nn>/ticket-owners.json` on main."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from types import ModuleType

import pytest
from conftest import SCRIPTS_DIR
from github_stub import HEAD_SHA, GitHubStub, changed, check_run, green_runs, review, serve
from pytest_bdd import given, parsers, scenarios, then, when
from test_merge_ready import run_script

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("merge_tiers.feature")

DOC_CHECK = "Doc checks (paths, citations, agent front matter, decider cells)"


def _review_tiers() -> ModuleType:
    path = SCRIPTS_DIR / "ci" / "review_tiers.py"
    spec = importlib.util.spec_from_file_location("review_tiers", path)
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses resolve their module by name
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def stub() -> GitHubStub:
    return GitHubStub(reviews=[])


@given(parsers.parse('a PR that changes only "{path}"'))
def only(stub: GitHubStub, path: str) -> None:
    stub.files = changed(path)


@given(parsers.parse('a PR that adds "{path}"'))
def adds(stub: GitHubStub, path: str) -> None:
    stub.files = changed(path, status="added")


@given(parsers.parse('a PR from the head branch "{branch}" that changes only "{path}"'))
def from_branch(stub: GitHubStub, branch: str, path: str) -> None:
    stub.pr["head"]["ref"] = branch
    stub.files = changed(path)


@given(parsers.parse('the PR also adds an extensionless file "{path}" with a shebang line'))
def hidden_code(stub: GitHubStub, path: str) -> None:
    stub.files += changed(path, status="added")
    stub.contents[(path, HEAD_SHA)] = b"#!/bin/sh\necho hidden\n"


@given(parsers.parse('the PR body says "{text}"'))
def body(stub: GitHubStub, text: str) -> None:
    stub.pr["body"] = text


@given(parsers.parse("the PR reports {count:d} changed files"))
def reports(stub: GitHubStub, count: int) -> None:
    stub.pr["changed_files"] = count


@given("the doc-check succeeded on the head")
def doc_check(stub: GitHubStub) -> None:
    stub.check_runs = [*green_runs(), check_run(DOC_CHECK, run_id=30)]


@given(parsers.parse("APPROVE verdicts from {roles} on the head"))
def approve(stub: GitHubStub, roles: str) -> None:
    for i, role in enumerate(r for r in re.split(r",\s*|\s+and\s+", roles) if r):
        stub.reviews.append(review(role, "APPROVE", review_id=10 + i))


@when("merge_ready.py runs", target_fixture="result")
def run_check(stub: GitHubStub) -> subprocess.CompletedProcess[str]:
    with serve(stub):
        return run_script(stub)


@when("the tier is computed", target_fixture="computed_tier")
def compute_tier(stub: GitHubStub) -> int:
    rt = _review_tiers()
    return int(rt.classify(rt.ChangedFile(f["filename"]) for f in stub.files).tier)


@then("it exits 0")
def exits_0(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert "merge-ready: yes" in result.stdout


@then(parsers.parse('it exits non-zero naming "{word}"'))
def refused(result: subprocess.CompletedProcess[str], word: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert "merge-ready: no" in result.stdout
    assert word in result.stdout, result.stdout


@then(parsers.parse('it exits 2 naming "{word}"'))
def unknown(result: subprocess.CompletedProcess[str], word: str) -> None:
    assert result.returncode == 2, result.stdout + result.stderr
    assert "merge-ready: unknown" in result.stdout
    assert word in result.stdout, result.stdout


@then(parsers.parse("the tier is {tier:d}"))
def tier_is(computed_tier: int, tier: int) -> None:
    assert computed_tier == tier
