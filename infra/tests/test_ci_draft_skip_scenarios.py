"""Binds tests/features/ci_draft_skip.feature (CI-DRAFT-SKIP; ST-002; PO 2026-10-18).

The job conditions of the real ci.yml are evaluated per event (workflow_if.py), the real
ci-gate step runs as a subprocess, and scripts/ci/merge_ready.py runs over HTTP against the
local GitHub API stub, as the orchestrator runs it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest
import yaml
from conftest import REPO_ROOT
from github_stub import GitHubStub, check_run, review, serve, workflow_run
from pytest_bdd import given, parsers, scenarios, then, when
from test_merge_ready import run_script
from workflow_if import DISPATCH, DRAFT_PR, PUSH, READY_PR, SCHEDULE, evaluate

pytestmark = [pytest.mark.scenario, pytest.mark.integration]
scenarios("ci_draft_skip.feature")

CI = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())
JOBS = CI["jobs"]
EVENTS = {
    "draft pull request": DRAFT_PR,
    "pull request ready for review": READY_PR,
    "push to main": PUSH,
    "nightly schedule": SCHEDULE,
    "manual dispatch": DISPATCH,
}


@when(parsers.parse("CI is triggered for a {event}"), target_fixture="running")
def triggered(event: str) -> set[str]:
    return {name for name, job in JOBS.items() if evaluate(job.get("if"), EVENTS[event])}


@then("no CI job runs, not even ci-gate")
def nothing_runs(running: set[str]) -> None:
    assert running == set(), f"jobs that would run (and could go red) on a draft: {running}"


@then(parsers.parse("every CI job runs except {skipped}"))
def all_but(running: set[str], skipped: str) -> None:
    assert running == set(JOBS) - set(skipped.split(" and "))


@then("ci-gate runs")
def gate_runs(running: set[str]) -> None:
    assert "ci-gate" in running


@then("CI is triggered when a pull request is marked ready for review or its labels change")
def ready_trigger() -> None:
    types = set(CI[True]["pull_request"]["types"])  # PyYAML reads `on:` as True
    assert {"ready_for_review", "labeled", "unlabeled", "opened", "synchronize"} <= types


@pytest.fixture
def stub() -> GitHubStub:
    return GitHubStub(reviews=[], check_runs=[], workflow_runs=[])


@given("a pull request whose CI jobs were all skipped because it is a draft")
def draft_runs(stub: GitHubStub) -> None:
    names = ["PR policy (test immutability, size)", "Python unit suites (time-budgeted)"]
    stub.check_runs = [
        check_run(n, conclusion="skipped", run_id=i + 1) for i, n in enumerate([*names, "ci-gate"])
    ]
    stub.workflow_runs = [workflow_run(1, 1, conclusion="skipped")]


@given("the principal-engineer and the senior-qa-engineer approved the head")
def both_approved(stub: GitHubStub) -> None:
    stub.reviews += [
        review("principal-engineer", "APPROVE", review_id=1),
        review("senior-qa-engineer", "APPROVE", review_id=2),
    ]


@when("the orchestrator runs the merge check on the head", target_fixture="result")
def run_check(stub: GitHubStub) -> subprocess.CompletedProcess[str]:
    with serve(stub):
        return run_script(stub)


@then(parsers.parse('the merge is refused naming "{word}"'))
def refused(result: subprocess.CompletedProcess[str], word: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert "merge-ready: no" in result.stdout
    assert word in result.stdout


@given(
    "a ready pull request whose PR policy job was skipped and every other gate passed",
    target_fixture="needs",
)
def policy_skipped() -> dict[str, dict[str, str]]:
    needs = {job: {"result": "success"} for job in JOBS["ci-gate"]["needs"]}
    needs["pr-policy"] = {"result": "skipped"}
    return needs


@when("the ci-gate step judges the results", target_fixture="gate")
def run_gate(needs: dict[str, dict[str, str]]) -> subprocess.CompletedProcess[str]:
    step = JOBS["ci-gate"]["steps"][0]
    env = {**os.environ, "RESULTS": json.dumps(needs), "EVENT": "pull_request"}
    script = step["run"].split("python3 -c '", 1)[1].rsplit("'", 1)[0]
    return subprocess.run(
        [sys.executable, "-c", script],
        input=env["RESULTS"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


@then(parsers.parse('ci-gate fails naming "{word}"'))
def gate_fails(gate: subprocess.CompletedProcess[str], word: str) -> None:
    assert gate.returncode == 1, gate.stdout + gate.stderr
    assert word in gate.stdout
