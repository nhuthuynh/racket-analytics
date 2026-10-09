"""CI-PR-GATE: `scripts/ci/merge_ready.py` refuses a merge into `main` unless every CI job
incl. ci-gate succeeded on the PR's head SHA and the principal-engineer and a senior reviewer
both posted "Verdict: APPROVE" on that SHA (PO rule 2026-10-07; user request 2026-10-08).

Unit tests drive the pure `evaluate()` rule (no I/O). Integration tests run the script as the
orchestrator does, over HTTP against a local GitHub API stub (`github_stub.py`).
Negative cases first.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from conftest import SCRIPTS_DIR
from github_stub import (
    HEAD_SHA,
    OLD_SHA,
    PR_NUMBER,
    REPO,
    GitHubStub,
    approvals,
    check_run,
    green_runs,
    review,
    serve,
    workflow_run,
)

SCRIPT = SCRIPTS_DIR / "ci" / "merge_ready.py"
FIXTURES = Path(__file__).parent / "fixtures"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("merge_ready", SCRIPT)
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pr(sha: str = HEAD_SHA, state: str = "open", base: str = "main") -> dict[str, Any]:
    return {"number": PR_NUMBER, "state": state, "head": {"sha": sha}, "base": {"ref": base}}


def evaluate(
    runs: list[dict[str, Any]] | None = None,
    reviews: list[dict[str, Any]] | None = None,
    the_pr: dict[str, Any] | None = None,
    sha: str = HEAD_SHA,
    wruns: list[dict[str, Any]] | None = None,
) -> list[str]:
    return load().evaluate(
        the_pr or pr(),
        sha,
        green_runs() if runs is None else runs,
        approvals() if reviews is None else reviews,
        [workflow_run()] if wruns is None else wruns,
    )


def suite(runs: list[dict[str, Any]], suite_id: int, id_offset: int) -> list[dict[str, Any]]:
    """The same jobs as another check suite (a new trigger of the workflow, e.g. a label)."""
    return [r | {"id": r["id"] + id_offset, "check_suite": {"id": suite_id}} for r in runs]


def red_suite() -> list[dict[str, Any]]:
    """What a pre-label run leaves behind: policy failed, the rest cancelled, ci-gate failed."""
    return [
        r
        | {
            "conclusion": "failure"
            if r["name"] in {"ci-gate", "PR policy (test immutability, size)"}
            else "cancelled"
        }
        for r in green_runs()
        if r["conclusion"] == "success"
    ]


# ======================================================================= unit: refusals
@pytest.mark.unit
def test_a_failed_job_blocks_the_merge() -> None:
    runs = [
        *green_runs(),
        check_run("Integration, scenario and regression suites", "failure", run_id=20),
    ]
    reasons = evaluate(runs=runs)
    assert any(
        "Integration, scenario and regression suites" in r and "failure" in r for r in reasons
    )


@pytest.mark.unit
def test_an_approval_on_an_older_sha_does_not_count() -> None:
    reviews = [
        review("principal-engineer", "APPROVE", HEAD_SHA, 1),
        review("senior-qa-engineer", "APPROVE", OLD_SHA, 2),
    ]
    reasons = evaluate(reviews=reviews)
    assert any("senior" in r and OLD_SHA in r for r in reasons)  # stale, not missing


@pytest.mark.unit
def test_a_missing_senior_verdict_blocks_the_merge() -> None:
    reasons = evaluate(reviews=[review("principal-engineer", "APPROVE")])
    assert any("senior" in r for r in reasons)


@pytest.mark.unit
def test_a_missing_principal_verdict_blocks_the_merge() -> None:
    reasons = evaluate(reviews=[review("senior-backend-engineer", "APPROVE")])
    assert any("principal-engineer" in r for r in reasons)


@pytest.mark.unit
def test_a_pending_ci_gate_blocks_the_merge() -> None:
    runs = [r for r in green_runs() if r["name"] != "ci-gate"]
    runs.append(check_run("ci-gate", conclusion=None, status="in_progress", run_id=30))
    reasons = evaluate(runs=runs)
    assert any("ci-gate" in r and "in_progress" in r for r in reasons)


@pytest.mark.unit
def test_no_ci_gate_run_at_all_blocks_the_merge() -> None:
    reasons = evaluate(runs=[r for r in green_runs() if r["name"] != "ci-gate"])
    assert any("ci-gate" in r for r in reasons)


@pytest.mark.unit
def test_a_skipped_ci_gate_blocks_the_merge() -> None:
    runs = [r for r in green_runs() if r["name"] != "ci-gate"]
    runs.append(check_run("ci-gate", conclusion="skipped", run_id=31))
    assert any("ci-gate" in r for r in evaluate(runs=runs))


@pytest.mark.unit
def test_the_latest_verdict_of_a_role_wins_changes_requested_after_approve() -> None:
    reviews = [
        *approvals(),
        review("principal-engineer", "CHANGES REQUESTED", HEAD_SHA, 9, "2026-10-08T11:00:00Z"),
    ]
    assert any("principal-engineer" in r for r in evaluate(reviews=reviews))


@pytest.mark.unit
def test_changes_requested_by_any_senior_on_the_head_blocks() -> None:
    reviews = [*approvals(), review("senior-backend-engineer", "CHANGES REQUESTED", HEAD_SHA, 5)]
    assert any("senior-backend-engineer" in r for r in evaluate(reviews=reviews))


@pytest.mark.unit
def test_a_verdict_not_at_the_start_of_the_body_does_not_count() -> None:
    late = review("senior-qa-engineer", "APPROVE", HEAD_SHA, 2)
    late["body"] = "Looks fine.\n" + late["body"]
    reasons = evaluate(reviews=[review("principal-engineer", "APPROVE"), late])
    assert any("senior" in r for r in reasons)


@pytest.mark.unit
def test_a_rerun_that_failed_after_a_success_blocks() -> None:
    runs = [*green_runs(), check_run("ci-gate", "failure", run_id=99)]
    assert any("ci-gate" in r and "failure" in r for r in evaluate(runs=runs))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("the_pr", "word"),
    [(pr(sha=OLD_SHA), "head"), (pr(state="closed"), "open"), (pr(base="sprint-03"), "main")],
)
def test_the_sha_must_be_the_head_of_an_open_pr_into_main(
    the_pr: dict[str, Any], word: str
) -> None:
    assert any(word in r for r in evaluate(the_pr=the_pr))


# ---------------------------------------------- unit: who and what may give a verdict (M1, M2)
@pytest.mark.unit
@pytest.mark.parametrize("association", ["NONE", "CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR"])
def test_a_verdict_from_an_untrusted_author_does_not_count(association: str) -> None:
    outsider = review("senior-qa-engineer", "APPROVE", review_id=2, association=association)
    reasons = evaluate(reviews=[review("principal-engineer", "APPROVE"), outsider])
    assert any(r.startswith("senior reviewer: no latest") for r in reasons)


@pytest.mark.unit
def test_an_untrusted_approve_does_not_override_a_real_changes_requested() -> None:
    reviews = [
        *approvals(),
        review("principal-engineer", "CHANGES REQUESTED", HEAD_SHA, 8, "2026-10-08T11:00:00Z"),
        review(
            "principal-engineer", "APPROVE", HEAD_SHA, 9, "2026-10-08T12:00:00Z", association="NONE"
        ),
    ]
    assert "principal-engineer: Verdict: CHANGES REQUESTED on the head" in evaluate(reviews=reviews)


@pytest.mark.unit
@pytest.mark.parametrize("state", ["PENDING", "DISMISSED"])
def test_an_unsubmitted_or_dismissed_review_does_not_count(state: str) -> None:
    unsent = review("senior-qa-engineer", "APPROVE", review_id=2, submitted_at=None, state=state)
    reasons = evaluate(reviews=[review("principal-engineer", "APPROVE"), unsent])
    assert any(r.startswith("senior reviewer: no latest") for r in reasons)


@pytest.mark.unit
def test_a_pending_approve_does_not_override_a_submitted_changes_requested() -> None:
    reviews = [
        *approvals(),
        review("senior-qa-engineer", "CHANGES REQUESTED", HEAD_SHA, 8, "2026-10-08T11:00:00Z"),
        review("senior-qa-engineer", "APPROVE", HEAD_SHA, 9, None, state="PENDING"),
    ]
    assert "senior-qa-engineer: Verdict: CHANGES REQUESTED on the head" in evaluate(reviews=reviews)


@pytest.mark.unit
@pytest.mark.parametrize(
    "body",
    [
        "Verdict: APPROVE\n\n> quoted earlier review\nReviewer: senior-qa-engineer\n",
        "Verdict: APPROVE\nSee the example below.\nReviewer: senior-qa-engineer\n",
        "Verdict: APPROVE\n",
    ],
)
def test_the_reviewer_line_must_follow_the_verdict_line(body: str) -> None:
    misplaced = review("senior-qa-engineer", "APPROVE", review_id=2) | {"body": body}
    reasons = evaluate(reviews=[review("principal-engineer", "APPROVE"), misplaced])
    assert any(r.startswith("senior reviewer: no latest") for r in reasons)


@pytest.mark.unit
def test_a_failure_is_not_hidden_by_a_same_named_success_in_another_workflow() -> None:
    runs = [
        *green_runs(),
        check_run("lint", "failure", run_id=60, suite_id=1),
        check_run("lint", "success", run_id=61, suite_id=2),
    ]
    assert any("'lint' is failure" in r for r in evaluate(runs=runs))


@pytest.mark.unit
@pytest.mark.parametrize("outcome", ["cancelled", "timed_out", "action_required", "failure"])
def test_a_non_gate_run_that_did_not_succeed_blocks(outcome: str) -> None:
    runs = [*green_runs(), check_run("E2E", outcome, run_id=70)]
    assert f"check 'E2E' is {outcome}" in evaluate(runs=runs)


# --------------------------------- unit: a newer run of the same workflow supersedes (M3)
@pytest.mark.unit
def test_a_newer_failing_suite_of_the_workflow_blocks_despite_an_older_green_one() -> None:
    runs = green_runs() + suite(red_suite(), 2, 100)
    wruns = [workflow_run(1, 1), workflow_run(2, 2)]
    reasons = evaluate(runs=runs, wruns=wruns)
    assert "check 'ci-gate' is failure" in reasons
    assert "check 'PR policy (test immutability, size)' is failure" in reasons


@pytest.mark.unit
def test_a_superseded_suite_never_hides_another_workflows_failure() -> None:
    runs = (
        red_suite()
        + suite(green_runs(), 2, 100)
        + [check_run("review", "failure", run_id=500, suite_id=3)]
    )
    wruns = [workflow_run(1, 1), workflow_run(2, 2), workflow_run(3, 3, workflow_id=11)]
    assert evaluate(runs=runs, wruns=wruns) == ["check 'review' is failure"]


@pytest.mark.unit
def test_a_newest_suite_cancelled_before_its_jobs_started_blocks() -> None:
    wruns = [workflow_run(1, 1), workflow_run(2, 2)]  # suite 2 has no check runs at all
    assert any("no ci-gate check run" in r for r in evaluate(wruns=wruns))


@pytest.mark.unit
def test_a_suite_of_another_event_is_not_superseded() -> None:
    runs = suite(red_suite(), 1, 0) + suite(green_runs(), 2, 100)
    wruns = [workflow_run(1, 1, event="workflow_dispatch"), workflow_run(2, 2)]
    assert "check 'ci-gate' is failure" in evaluate(runs=runs, wruns=wruns)


@pytest.mark.unit
def test_without_workflow_run_data_every_suite_still_counts() -> None:
    runs = red_suite() + suite(green_runs(), 2, 100)
    assert "check 'ci-gate' is failure" in evaluate(runs=runs, wruns=[])


# ======================================================================= unit: allowed
@pytest.mark.unit
def test_all_green_and_both_approvals_on_the_head_allow_the_merge() -> None:
    assert evaluate() == []


@pytest.mark.unit
def test_a_successful_rerun_replaces_an_earlier_failure() -> None:
    runs = [check_run("ci-gate", "failure", run_id=1)] + [
        r | {"id": r["id"] + 100} for r in green_runs()
    ]
    assert evaluate(runs=runs) == []


@pytest.mark.unit
def test_a_label_rerun_supersedes_the_cancelled_and_failed_older_suite() -> None:
    runs = red_suite() + suite(green_runs(), 2, 100)
    wruns = [workflow_run(1, 1), workflow_run(2, 2)]
    assert evaluate(runs=runs, wruns=wruns) == []


@pytest.mark.unit
def test_regression_merged_pr_2_head_with_a_label_rerun_is_merge_ready_on_ci() -> None:
    """Real check and workflow runs of PR #2 at c4c66b1 (review round 2, M3): suite
    101621087376 was cancelled by the label re-run, suite 101621285156 is all green."""
    data = json.loads((FIXTURES / "pr2_c4c66b1_runs.json").read_text())
    sha = data["head_sha"]
    reasons = load().check_reasons(data["check_runs"], sha, data["workflow_runs"])
    assert reasons == []


@pytest.mark.unit
def test_a_neutral_non_gate_run_allows_the_merge() -> None:
    assert evaluate(runs=[*green_runs(), check_run("Optional report", "neutral", run_id=71)]) == []


@pytest.mark.unit
@pytest.mark.parametrize("association", ["OWNER", "MEMBER", "COLLABORATOR"])
def test_a_trusted_author_may_give_the_senior_verdict(association: str) -> None:
    senior = review("senior-qa-engineer", "APPROVE", review_id=2, association=association)
    assert evaluate(reviews=[review("principal-engineer", "APPROVE"), senior]) == []


@pytest.mark.unit
def test_the_latest_review_wins_when_the_api_lists_them_out_of_order() -> None:
    reviews = [
        review("principal-engineer", "APPROVE", HEAD_SHA, 9, "2026-10-08T12:00:00Z"),
        review("principal-engineer", "CHANGES REQUESTED", HEAD_SHA, 8, "2026-10-08T11:00:00Z"),
        review("senior-qa-engineer", "APPROVE", HEAD_SHA, 2),
    ]
    assert evaluate(reviews=reviews) == []


# ======================================================================= integration
def run_script(
    stub: GitHubStub, sha: str = HEAD_SHA, token: str | None = None, pr: int = PR_NUMBER
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in {"GITHUB_TOKEN", "GH_TOKEN"}}
    env["GITHUB_API_URL"] = stub.url
    if token:
        env["GITHUB_TOKEN"] = token
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", REPO, "--pr", str(pr), "--sha", sha],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )


@pytest.mark.integration
def test_script_refuses_a_failed_job_over_http_and_exits_1() -> None:
    stub = GitHubStub(check_runs=[*green_runs(), check_run("E2E", "failure", run_id=50)])
    with serve(stub):
        res = run_script(stub)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "E2E" in res.stdout
    assert "merge-ready: no" in res.stdout


@pytest.mark.integration
def test_script_refuses_a_stale_sha_over_http() -> None:
    with serve(GitHubStub()) as stub:
        res = run_script(stub, sha=OLD_SHA)
    assert res.returncode == 1
    assert "merge-ready: no" in res.stdout
    assert f"{OLD_SHA} is not the PR head" in res.stdout


@pytest.mark.integration
def test_script_exits_2_when_the_api_cannot_be_read() -> None:
    stub = GitHubStub(pr={"message": "x"})
    stub.url = "http://127.0.0.1:9"  # nothing listens on the discard port
    res = run_script(stub)
    assert res.returncode == 2
    assert "merge-ready: unknown" in res.stdout


@pytest.mark.integration
@pytest.mark.parametrize(
    ("stub_kwargs", "pr_number"),
    [({}, 404), ({"raw_pr": b"<html>not json</html>"}, None)],
    ids=["http-404", "non-json-body"],
)
def test_script_exits_2_on_an_http_error_or_a_malformed_body(
    stub_kwargs: dict[str, Any], pr_number: int | None
) -> None:
    with serve(GitHubStub(**stub_kwargs)) as stub:
        res = run_script(stub, pr=pr_number or PR_NUMBER)
    assert res.returncode == 2, res.stdout + res.stderr
    assert "merge-ready: unknown" in res.stdout
    assert "Traceback" not in res.stderr


@pytest.mark.integration
def test_script_allows_the_merge_following_every_page_and_sends_the_token() -> None:
    stub = GitHubStub(page_size=2)  # 5 check runs -> 3 pages; 2 reviews -> 1 page
    with serve(stub):
        res = run_script(stub, token="t0ken")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "merge-ready: yes" in res.stdout
    check_pages = [p for p, _ in stub.requests if "/check-runs" in p]
    assert len(check_pages) == 3
    assert {auth for _, auth in stub.requests} == {"Bearer t0ken"}


@pytest.mark.integration
def test_script_refuses_when_the_newest_ci_run_failed_over_http() -> None:
    stub = GitHubStub(
        check_runs=green_runs() + suite(red_suite(), 2, 100),
        workflow_runs=[workflow_run(2, 2), workflow_run(1, 1)],
    )
    with serve(stub):
        res = run_script(stub)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "check 'ci-gate' is failure" in res.stdout


@pytest.mark.integration
def test_script_allows_a_label_rerun_and_asks_for_the_head_shas_workflow_runs() -> None:
    stub = GitHubStub(
        check_runs=red_suite() + suite(green_runs(), 2, 100),
        workflow_runs=[workflow_run(1, 1), workflow_run(2, 2), workflow_run(9, 9, sha=OLD_SHA)],
        page_size=1,
    )
    with serve(stub):
        res = run_script(stub)
    assert res.returncode == 0, res.stdout + res.stderr
    asked = [p for p, _ in stub.requests if "/actions/runs" in p]
    assert len(asked) == 2  # two runs on the head SHA, one per page
    assert all(f"head_sha={HEAD_SHA}" in p for p in asked)


@pytest.mark.unit
def test_an_empty_api_url_falls_back_to_github(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = load()
    seen: list[str] = []

    def fake_get(url: str) -> tuple[Any, None]:
        seen.append(url)
        raise OSError("offline")

    monkeypatch.setattr(mod, "_get", fake_get)
    monkeypatch.setenv("GITHUB_API_URL", "")
    assert mod.main(["--repo", REPO, "--pr", "7", "--sha", HEAD_SHA]) == 2
    assert seen == [f"https://api.github.com/repos/{REPO}/pulls/7"]


# ============ CI-MERGE-READY-CANCELLED: a run the concurrency group cancelled is not current
# PR #49 at 6342f36: two CI pull_request runs started in the same second; the higher id was
# cancelled before any job started (a suite with no check runs), the lower id is all green.
# Rule: a cancelled workflow run is never current while a non-cancelled run of the same
# (workflow, event) exists on the SHA; among those the newest counts, so a newer failed or
# in-progress run still wins. If every run is cancelled, say so. Negative cases first.
def cancelled(suite_id: int, run_id: int, **kw: Any) -> dict[str, Any]:
    return workflow_run(suite_id, run_id, conclusion="cancelled", **kw)


@pytest.mark.unit
def test_a_newer_failed_run_beats_an_older_green_one_even_with_a_cancelled_newest() -> None:
    runs = green_runs() + suite(red_suite(), 2, 100)
    wruns = [
        workflow_run(1, 1, conclusion="success"),
        workflow_run(2, 2, conclusion="failure"),
        cancelled(3, 3),
    ]
    reasons = evaluate(runs=runs, wruns=wruns)
    assert "check 'ci-gate' is failure" in reasons
    assert not any("no ci-gate" in r for r in reasons)


@pytest.mark.unit
def test_a_newer_in_progress_run_blocks_despite_an_older_green_one() -> None:
    runs = [*green_runs(), check_run("ci-gate", None, "in_progress", run_id=200, suite_id=2)]
    wruns = [workflow_run(1, 1, conclusion="success"), workflow_run(2, 2, status="in_progress")]
    assert "check 'ci-gate' is in_progress" in evaluate(runs=runs, wruns=wruns)


@pytest.mark.unit
def test_a_newer_queued_run_without_check_runs_yet_blocks() -> None:
    wruns = [workflow_run(1, 1, conclusion="success"), workflow_run(2, 2, status="queued")]
    assert any("no ci-gate check run" in r for r in evaluate(wruns=wruns))


@pytest.mark.unit
def test_all_runs_cancelled_is_reported_explicitly() -> None:
    wruns = [cancelled(1, 1), cancelled(2, 2)]
    reasons = evaluate(runs=[], wruns=wruns)
    assert f"all CI runs on {HEAD_SHA} were cancelled" in reasons


@pytest.mark.unit
def test_all_runs_cancelled_with_leftover_check_runs_still_blocks() -> None:
    runs = red_suite()  # suite 1 cancelled after some jobs ran
    wruns = [cancelled(1, 1), cancelled(2, 2)]
    reasons = evaluate(runs=runs, wruns=wruns)
    assert f"all CI runs on {HEAD_SHA} were cancelled" in reasons


@pytest.mark.unit
def test_a_cancelled_run_of_another_event_does_not_rescue_a_failure() -> None:
    runs = red_suite() + suite(green_runs(), 2, 100)
    wruns = [workflow_run(1, 1, conclusion="failure"), cancelled(2, 2, event="push")]
    assert "check 'ci-gate' is failure" in evaluate(runs=runs, wruns=wruns)


@pytest.mark.unit
def test_a_rerun_job_that_failed_in_the_green_suite_blocks() -> None:
    runs = [*green_runs(), check_run("ci-gate", "failure", run_id=99, suite_id=1)]
    wruns = [workflow_run(1, 1, conclusion="failure"), cancelled(2, 2)]
    assert "check 'ci-gate' is failure" in evaluate(runs=runs, wruns=wruns)


@pytest.mark.unit
def test_a_newer_cancelled_run_does_not_supersede_an_older_green_one() -> None:
    """The exact PR #49 shape: newer run cancelled with no check runs, older run green."""
    wruns = [workflow_run(1, 1, conclusion="success"), cancelled(2, 2)]
    assert evaluate(wruns=wruns) == []


@pytest.mark.unit
def test_a_successful_rerun_of_a_job_in_the_green_suite_counts() -> None:
    runs = [
        *[r for r in green_runs() if r["name"] != "ci-gate"],
        check_run("ci-gate", "failure", run_id=4, suite_id=1),
        check_run("ci-gate", "success", run_id=99, suite_id=1),  # re-run of the job
    ]
    wruns = [workflow_run(1, 1, conclusion="success"), cancelled(2, 2)]
    assert evaluate(runs=runs, wruns=wruns) == []


@pytest.mark.unit
def test_an_older_cancelled_run_is_still_superseded_by_a_newer_green_one() -> None:
    runs = red_suite() + suite(green_runs(), 2, 100)
    wruns = [cancelled(1, 1), workflow_run(2, 2, conclusion="success")]
    assert evaluate(runs=runs, wruns=wruns) == []


@pytest.mark.unit
def test_regression_pr_49_head_with_a_concurrency_cancelled_newer_run_is_ready_on_ci() -> None:
    """Real check and workflow runs of PR #49 at 6342f36 (fetched 2026-10-09): CI run
    37934889373 (cancelled, suite 102781271159, no check runs) and 37934889367 (all green)."""
    data = json.loads((FIXTURES / "pr49_6342f36_runs.json").read_text())
    reasons = load().check_reasons(data["check_runs"], data["head_sha"], data["workflow_runs"])
    assert reasons == []


@pytest.mark.integration
def test_script_reports_all_cancelled_over_http_and_exits_1() -> None:
    stub = GitHubStub(
        check_runs=[],
        workflow_runs=[cancelled(1, 1), cancelled(2, 2)],
    )
    with serve(stub):
        res = run_script(stub)
    assert res.returncode == 1, res.stdout + res.stderr
    assert f"all CI runs on {HEAD_SHA} were cancelled" in res.stdout


@pytest.mark.integration
def test_script_allows_pr_49_shape_over_http() -> None:
    data = json.loads((FIXTURES / "pr49_6342f36_runs.json").read_text())
    sha = data["head_sha"]
    stub = GitHubStub(
        pr=pr(sha=sha),
        check_runs=data["check_runs"],
        reviews=approvals(sha),
        workflow_runs=data["workflow_runs"],
        page_size=5,
    )
    with serve(stub):
        res = run_script(stub, sha=sha)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "merge-ready: yes" in res.stdout


# ============ PE-1 (review round 1): only a REPLACED cancelled run is ignored
# pr-policy reads the PR labels from the event payload, so a newer run that removed a label and
# was then cancelled by hand or by infra (no run after it) stands for a label state the older
# green run never saw. A cancelled run is ignored only when a non-cancelled run of the same
# (workflow, event) was created in the same second or later; otherwise it stays current and
# blocks. Missing created_at never makes a cancelled run ignorable. Negative cases first.
T0 = "2026-10-09T13:00:00Z"
T1 = "2026-10-09T13:05:00Z"


@pytest.mark.unit
def test_a_later_cancelled_run_that_nothing_replaced_blocks_despite_an_older_green_one() -> None:
    wruns = [
        workflow_run(1, 1, conclusion="success", created_at=T0),
        cancelled(2, 2, created_at=T1),
    ]
    reasons = evaluate(wruns=wruns)
    assert reasons, "a cancelled newest run must not let the older green run decide"
    assert f"the newest CI run on {HEAD_SHA} was cancelled and no later run replaced it" in reasons


@pytest.mark.unit
def test_a_cancelled_run_without_created_at_is_not_ignored() -> None:
    wruns = [workflow_run(1, 1, conclusion="success"), cancelled(2, 2, created_at=None)]
    assert any("was cancelled" in r for r in evaluate(wruns=wruns))


@pytest.mark.unit
def test_a_green_run_without_created_at_does_not_replace_a_cancelled_one() -> None:
    wruns = [workflow_run(1, 1, conclusion="success", created_at=None), cancelled(2, 2)]
    assert any("was cancelled" in r for r in evaluate(wruns=wruns))


@pytest.mark.unit
def test_a_later_cancelled_run_with_a_failed_newer_run_reports_the_failure() -> None:
    runs = green_runs() + suite(red_suite(), 3, 100)
    wruns = [
        workflow_run(1, 1, conclusion="success", created_at=T0),
        cancelled(2, 2, created_at=T1),
        workflow_run(3, 3, conclusion="failure", created_at=T1),
    ]
    reasons = evaluate(runs=runs, wruns=wruns)
    assert "check 'ci-gate' is failure" in reasons
    assert not any("was cancelled" in r for r in reasons)


@pytest.mark.unit
def test_a_cancelled_run_replaced_by_a_later_green_run_is_ignored() -> None:
    runs = suite(green_runs(), 3, 100)
    wruns = [
        workflow_run(1, 1, conclusion="success", created_at=T0),
        cancelled(2, 2, created_at=T0),
        workflow_run(3, 3, conclusion="success", created_at=T1),
    ]
    assert evaluate(runs=runs, wruns=wruns) == []


@pytest.mark.unit
def test_same_second_cancelled_run_is_still_ignored_pr_49() -> None:
    wruns = [
        workflow_run(1, 1, conclusion="success", created_at=T1),
        cancelled(2, 2, created_at=T1),
    ]
    assert evaluate(wruns=wruns) == []


@pytest.mark.integration
def test_script_refuses_a_later_unreplaced_cancelled_run_over_http() -> None:
    stub = GitHubStub(
        workflow_runs=[
            workflow_run(1, 1, conclusion="success", created_at=T0),
            cancelled(2, 2, created_at=T1),
        ],
    )
    with serve(stub):
        res = run_script(stub)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "merge-ready: no" in res.stdout
    assert "was cancelled and no later run replaced it" in res.stdout
