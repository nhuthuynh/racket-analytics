"""CI-DRAFT-SKIP unit tests: the draft guard on every ci.yml job, ci-gate still always(),
the triggers that start CI once a PR is ready, and the expression evaluator they rely on."""

from __future__ import annotations

import pytest
import yaml
from conftest import REPO_ROOT
from workflow_if import DISPATCH, DRAFT_PR, PUSH, READY_PR, SCHEDULE, evaluate

pytestmark = pytest.mark.unit

WF = REPO_ROOT / ".github" / "workflows"
CI = yaml.safe_load((WF / "ci.yml").read_text())
DRAFT_GUARD = "!github.event.pull_request.draft"


# ------------------------------------------------------------------ evaluator (negative first)
def test_evaluator_refuses_an_expression_it_does_not_understand() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        evaluate("success() && github.event_name == 'push'", PUSH)


def test_evaluator_reads_a_missing_context_as_null() -> None:
    assert evaluate(f"github.event_name != 'pull_request' || {DRAFT_GUARD}", PUSH) is True
    assert evaluate("github.event.pull_request.draft", PUSH) is False


def test_evaluator_applies_and_or_not_and_parentheses() -> None:
    expr = f"always() && (github.event_name != 'pull_request' || {DRAFT_GUARD})"
    assert evaluate(expr, DRAFT_PR) is False
    assert evaluate(expr, READY_PR) is True
    assert evaluate(None, DRAFT_PR) is True


# ------------------------------------------------------------------ ci.yml
@pytest.mark.parametrize("name", sorted(CI["jobs"]))
def test_every_ci_job_is_skipped_on_a_draft_pull_request(name: str) -> None:
    cond = CI["jobs"][name].get("if")
    assert cond is not None, f"{name}: no if: condition"
    assert DRAFT_GUARD in cond, f"{name}: no draft guard ({cond!r})"
    assert evaluate(cond, DRAFT_PR) is False, name


def test_ci_gate_stays_always_for_every_non_draft_event() -> None:
    cond = CI["jobs"]["ci-gate"]["if"]
    assert cond.replace(" ", "").startswith("always()&&("), cond
    for event in (READY_PR, PUSH, SCHEDULE, DISPATCH):
        assert evaluate(cond, event) is True, event


def test_guard_does_not_change_which_jobs_run_outside_drafts() -> None:
    jobs = CI["jobs"]
    for event in (READY_PR, PUSH, SCHEDULE, DISPATCH):
        run = {n for n, j in jobs.items() if evaluate(j.get("if"), event)}
        pr_only = set() if event is READY_PR else {"pr-policy"}
        nightly = {"flaky-report"} if event in (READY_PR, PUSH) else set()
        assert run == set(jobs) - pr_only - nightly, event


def test_ci_starts_when_a_pull_request_is_marked_ready_or_relabelled() -> None:
    types = set(CI[True]["pull_request"]["types"])
    assert {"ready_for_review", "labeled", "unlabeled"} <= types


def test_claude_review_skips_drafts_too() -> None:
    doc = yaml.safe_load((WF / "claude-review.yml").read_text())
    assert "github.event.pull_request.draft == false" in doc["jobs"]["review"]["if"]
    assert "ready_for_review" in doc[True]["pull_request"]["types"]
