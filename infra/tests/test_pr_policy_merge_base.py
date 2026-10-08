"""CI-POLICY-BASE integration tests: the `pr-policy` steps of ci.yml, run verbatim on a real
merge-ref checkout (pr_checkout.py), judge only the PR's own change set (NFR-077, NFR-078).

Incident: CI run 37739461709 (job 113186548205): docs-only PR #6 failed test immutability on
E2E_SPEC, which PR #9 changed on `main` 11 s before the run; the job diffed from the event's
stale `pull_request.base.sha`. The four incident cases are the Gherkin scenarios
(test_pr_policy_scenarios.py); these cover the edges around them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pr_checkout import E2E_SPEC, IMMUTABILITY_STEP, SIZE_STEP, PullRequest, git, policy_steps


@pytest.fixture
def pr(tmp_path: Path) -> PullRequest:
    return PullRequest.opened_against_main(tmp_path)


@pytest.mark.integration
@pytest.mark.parametrize("step", [IMMUTABILITY_STEP, SIZE_STEP])
def test_a_missing_base_branch_fails_closed(pr: PullRequest, step: str) -> None:
    pr.open_event("docs/notes.md", "# notes\n")
    pr.checkout_merge_ref()
    git(pr.runner, "update-ref", "-d", "refs/remotes/origin/main")
    res = pr.run_policy()[step]
    assert res.returncode == 2, res.stdout + res.stderr


@pytest.mark.integration
def test_without_a_moving_main_the_gate_is_unchanged(pr: PullRequest) -> None:
    pr.open_event(E2E_SPEC, "test('resume', () => { /* weakened */ })\n")
    pr.checkout_merge_ref()
    res = pr.run_policy()[IMMUTABILITY_STEP]
    assert res.returncode == 1, res.stdout + res.stderr
    assert f"modified: {E2E_SPEC}" in res.stdout


@pytest.mark.unit
def test_policy_steps_diff_from_the_base_branch_never_the_event_base_sha() -> None:
    steps = {s["name"]: json.dumps(s) for s in policy_steps()}
    for name in (IMMUTABILITY_STEP, SIZE_STEP):
        assert "pull_request.base.sha" not in steps[name]
        assert '--base \\"origin/$BASE_REF\\"' in steps[name]
        assert "github.base_ref" in steps[name]
