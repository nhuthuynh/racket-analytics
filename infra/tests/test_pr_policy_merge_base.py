"""CI-POLICY-BASE: the PR-policy job judges only the PR's own change set (EP/ENG-28, NFR-078;
EP/ENG-04, NFR-077).

Incident: CI run 37739461709 (job 113186548205, PR #6, docs only) failed test immutability on
`web/e2e/sprint-01/resumable-upload.spec.ts`. PR #9 had changed that spec on `main` 11 s before
the run. The job diffed `github.event.pull_request.base.sha...HEAD`; `HEAD` is the PR merge ref,
which GitHub had already rebuilt on the newer `main`, so the stale event base blamed `main`'s
change on the PR.

The integration tests below rebuild that situation with real git: an `origin` remote, a PR
branch, `main` moving after the event, and the runner's checkout of the merge ref with full
history (`fetch-depth: 0`). They then run the `pr-policy` steps exactly as written in
`.github/workflows/ci.yml`, with each `${{ ... }}` expression filled in from the event.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pr_checkout import (
    E2E_SPEC,
    IMMUTABILITY_STEP,
    SIZE_STEP,
    PullRequest,
    git,
    lines,
    pr_policy_steps,
    run_step,
)

MOVED_SPEC = E2E_SPEC


@pytest.fixture
def pr(tmp_path: Path) -> PullRequest:
    return PullRequest.opened_against_main(tmp_path)


# ---------------------------------------------------------------- negative cases first
@pytest.mark.integration
def test_a_docs_only_pr_is_not_blamed_for_a_test_edit_that_reached_main_after_the_event(
    pr: PullRequest,
) -> None:
    pr.change_in_pr("docs/notes.md", "# notes\n\nmore\n")
    pr.open_event()
    pr.main_moves(MOVED_SPEC, "test('resume', () => { /* hold one chunk */ })\n")
    pr.checkout_merge_ref()

    res = run_step(IMMUTABILITY_STEP, pr)

    assert res.returncode == 0, res.stdout + res.stderr
    assert MOVED_SPEC not in res.stdout


@pytest.mark.integration
def test_a_small_pr_is_not_blamed_for_lines_that_reached_main_after_the_event(
    pr: PullRequest,
) -> None:
    pr.change_in_pr("docs/change.md", lines(10))
    pr.open_event()
    pr.main_moves("backend/src/big.py", lines(450))
    pr.checkout_merge_ref()

    res = run_step(SIZE_STEP, pr)

    assert res.returncode == 0, res.stdout + res.stderr
    assert "pr-size: 10 changed lines" in res.stdout


@pytest.mark.integration
@pytest.mark.parametrize("step", [IMMUTABILITY_STEP, SIZE_STEP])
def test_a_missing_base_branch_fails_closed(pr: PullRequest, step: str) -> None:
    pr.change_in_pr("docs/notes.md", "# notes\n\nmore\n")
    pr.open_event()
    pr.checkout_merge_ref()
    git(pr.runner, "update-ref", "-d", "refs/remotes/origin/main")

    res = run_step(step, pr)

    assert res.returncode == 2, res.stdout + res.stderr


# ---------------------------------------------------------------- positive controls
@pytest.mark.integration
def test_a_test_edit_in_the_pr_is_still_caught_when_main_moved(pr: PullRequest) -> None:
    pr.change_in_pr("backend/tests/unit/test_a.py", "def test_a():\n    pass\n")
    pr.open_event()
    pr.main_moves(MOVED_SPEC, "test('resume', () => { /* hold one chunk */ })\n")
    pr.checkout_merge_ref()

    res = run_step(IMMUTABILITY_STEP, pr)

    assert res.returncode == 1, res.stdout + res.stderr
    assert "modified: backend/tests/unit/test_a.py" in res.stdout
    assert MOVED_SPEC not in res.stdout


@pytest.mark.integration
def test_an_oversize_pr_still_fails_when_main_moved(pr: PullRequest) -> None:
    pr.change_in_pr("backend/src/big.py", lines(401))
    pr.open_event()
    pr.main_moves("docs/notes.md", lines(30))
    pr.checkout_merge_ref()

    res = run_step(SIZE_STEP, pr)

    assert res.returncode == 1, res.stdout + res.stderr
    assert "pr-size: 401 changed lines" in res.stdout


@pytest.mark.integration
def test_without_a_moving_main_the_gate_is_unchanged(pr: PullRequest) -> None:
    pr.change_in_pr(MOVED_SPEC, "test('resume', () => { /* weakened */ })\n")
    pr.open_event()
    pr.checkout_merge_ref()

    res = run_step(IMMUTABILITY_STEP, pr)

    assert res.returncode == 1, res.stdout + res.stderr
    assert f"modified: {MOVED_SPEC}" in res.stdout


# ---------------------------------------------------------------- workflow wiring (unit)
@pytest.mark.unit
@pytest.mark.parametrize("step", [IMMUTABILITY_STEP, SIZE_STEP])
def test_policy_steps_never_diff_against_the_event_base_sha(step: str) -> None:
    (s,) = [x for x in pr_policy_steps() if x.get("name") == step]
    text = json.dumps(s)
    assert "pull_request.base.sha" not in text
    assert "github.base_ref" in text
