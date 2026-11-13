"""QA-WIP-GATE (story PRC-06; atomic item PRC-12.1; goal metric G06-10; ADR 0056 decision 3;
working-agreement §3 "Flow and WIP limits"): `scripts/measure/wip_gate.py --stage start`
refuses a ticket start at a full stage, from GitHub REST counts of the open ticket PRs.

Unit tests drive the pure functions on stubbed REST JSON; integration tests run the script over
real HTTP against `wip_stub.py`. Negative case first: 3 PRs in review, so a 4th start is
refused (today the orchestrator starts it; sprint-06 §0.1 "WIP 12 in review vs limit 3").
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import Sequence
from types import ModuleType
from typing import Any

import pytest
from conftest import SCRIPTS_DIR
from wip_stub import PE, QA, REPO, WipStub, gate_run, head_of, review, serve, ticket_pr

SCRIPT = SCRIPTS_DIR / "measure" / "wip_gate.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("wip_gate", SCRIPT)
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def counts(stub: WipStub) -> dict[str, int]:
    return load().count_stages(stub.pulls, stub.reviews, stub.check_runs)


def refusals(stub: WipStub) -> list[str]:
    return load().start_refusals(counts(stub))


# ------------------------------------------------------------------ unit: the start rule


@pytest.mark.unit
def test_a_fourth_start_is_refused_while_three_prs_are_in_review() -> None:
    stub = WipStub()
    for n in (1, 2, 3):
        stub.in_review(n)
    found = refusals(stub)
    assert len(found) == 1
    assert found[0].startswith("in review 3 of 3")


@pytest.mark.unit
def test_a_start_is_allowed_while_every_stage_has_room() -> None:
    stub = WipStub()
    stub.in_review(1)
    stub.in_review(2)
    stub.awaiting_qa(3)
    for n in (4, 5, 6):
        stub.in_progress(n)
    assert counts(stub) == {"in progress": 3, "in review": 2, "awaiting QA": 1, "awaiting merge": 0}
    assert refusals(stub) == []


@pytest.mark.unit
def test_a_start_that_would_put_a_fifth_ticket_in_progress_is_refused() -> None:
    stub = WipStub()
    for n in (1, 2, 3, 4):
        stub.in_progress(n)
    found = refusals(stub)
    assert len(found) == 1
    assert found[0].startswith("in progress 4 of 4")


@pytest.mark.unit
def test_a_start_is_refused_while_two_prs_await_qa() -> None:
    stub = WipStub()
    stub.awaiting_qa(1)
    stub.awaiting_qa(2)
    found = refusals(stub)
    assert [f.split(" of ")[0] for f in found] == ["awaiting QA 2"]


@pytest.mark.unit
def test_a_start_is_refused_while_one_pr_awaits_merge() -> None:
    stub = WipStub()
    stub.awaiting_merge(1)
    found = refusals(stub)
    assert [f.split(" of ")[0] for f in found] == ["awaiting merge 1"]


@pytest.mark.unit
def test_every_full_stage_is_named() -> None:
    stub = WipStub()
    for n in (1, 2, 3):
        stub.in_review(n)
    stub.awaiting_merge(4)
    found = refusals(stub)
    assert [f.split(" of ")[0] for f in found] == ["in review 3", "awaiting merge 1"]


@pytest.mark.unit
def test_other_limits_can_be_passed() -> None:
    stub = WipStub()
    for n in (1, 2, 3):
        stub.in_review(n)
    assert load().start_refusals(counts(stub), (4, 4, 2, 1)) == []


# ------------------------------------------------------------------ unit: stage of one PR


def stage(
    pr: dict[str, Any], reviews: Sequence[dict[str, Any]] = (), runs: Sequence[Any] = ()
) -> Any:
    return load().stage_of(pr, list(reviews), list(runs))


@pytest.mark.unit
def test_a_draft_ticket_pr_is_in_progress() -> None:
    assert stage(ticket_pr(1, draft=True)) == "in progress"


@pytest.mark.unit
def test_a_ready_pr_without_verdicts_is_in_review() -> None:
    assert stage(ticket_pr(1)) == "in review"


@pytest.mark.unit
def test_a_principal_engineer_approve_on_the_head_without_a_qa_verdict_awaits_qa() -> None:
    assert stage(ticket_pr(1), [review(PE, head_of(1))]) == "awaiting QA"


@pytest.mark.unit
def test_an_approve_on_an_older_head_does_not_move_the_pr() -> None:
    old = "f" * 40
    assert stage(ticket_pr(1), [review(PE, old)]) == "in review"
    assert stage(ticket_pr(1), [review(PE, old), review(QA, old)], [gate_run()]) == "in review"


@pytest.mark.unit
def test_a_qa_changes_requested_on_the_head_sends_the_pr_back_to_review() -> None:
    reviews = [review(PE, head_of(1)), review(QA, head_of(1), "CHANGES REQUESTED")]
    assert stage(ticket_pr(1), reviews, [gate_run()]) == "in review"


@pytest.mark.unit
def test_both_approves_and_a_green_ci_gate_on_the_head_await_merge() -> None:
    reviews = [review(PE, head_of(1)), review(QA, head_of(1))]
    assert stage(ticket_pr(1), reviews, [gate_run()]) == "awaiting merge"


@pytest.mark.unit
@pytest.mark.parametrize(
    "runs", [[], [gate_run("failure")], [gate_run(name="unit")]], ids=["none", "red", "other"]
)
def test_both_approves_without_a_green_ci_gate_stay_in_review(runs: list[Any]) -> None:
    reviews = [review(PE, head_of(1)), review(QA, head_of(1))]
    assert stage(ticket_pr(1), reviews, runs) == "in review"


@pytest.mark.unit
def test_an_approve_from_an_untrusted_author_does_not_count() -> None:
    reviews = [review(PE, head_of(1), association="NONE")]
    assert stage(ticket_pr(1), reviews) == "in review"


@pytest.mark.unit
def test_only_open_ticket_prs_into_main_are_counted() -> None:
    stub = WipStub()
    stub.pulls += [ticket_pr(1, ticket=""), ticket_pr(2, base="s06/other"), ticket_pr(3)]
    assert stage(stub.pulls[0]) is None
    assert stage(stub.pulls[1]) is None
    assert counts(stub)["in review"] == 1


@pytest.mark.unit
def test_the_stage_line_is_the_one_flow_metrics_parses() -> None:
    line = load().stage_line(
        {"in progress": 1, "in review": 2, "awaiting QA": 0, "awaiting merge": 0}
    )
    assert line == "In progress 1 · in review 2 · awaiting QA 0 · awaiting merge 0"
    flow = importlib.util.spec_from_file_location("fm", SCRIPTS_DIR / "measure" / "flow_metrics.py")
    assert flow
    assert flow.loader
    fm = importlib.util.module_from_spec(flow)
    flow.loader.exec_module(fm)
    match = fm.STAGE_LINE.search(line)
    assert match
    assert match.groups() == ("1", "2", "0", "0")


# ------------------------------------------------------------------ integration: over HTTP


def run_script(stub: WipStub, *extra: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in {"GITHUB_TOKEN", "GH_TOKEN"}}
    env["GITHUB_API_URL"] = stub.url
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", REPO, "--stage", "start", *extra],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


@pytest.mark.integration
def test_the_script_refuses_a_fourth_start_over_rest_and_names_the_stage() -> None:
    stub = WipStub()
    for n in (1, 2, 3):
        stub.in_review(n)
    with serve(stub):
        result = run_script(stub)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "In progress 0 · in review 3 · awaiting QA 0 · awaiting merge 0" in result.stdout
    assert "wip-gate: start refused: in review 3 of 3" in result.stdout
    # REST only, paged past the end (two items a page): no GraphQL, no Link header.
    assert all(r.startswith(f"/repos/{REPO}/") for r in stub.requests), stub.requests
    assert any("page=3" in r for r in stub.requests if "/pulls?" in r)


@pytest.mark.integration
def test_the_script_reads_reviews_and_check_runs_for_the_awaiting_merge_count() -> None:
    stub = WipStub()
    stub.awaiting_merge(7)
    stub.in_progress(8)
    with serve(stub):
        result = run_script(stub)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "In progress 1 · in review 0 · awaiting QA 0 · awaiting merge 1" in result.stdout
    assert "awaiting merge 1 of 1" in result.stdout
    assert any(r.startswith(f"/repos/{REPO}/pulls/7/reviews") for r in stub.requests)
    assert any(f"/commits/{head_of(7)}/check-runs" in r for r in stub.requests)


@pytest.mark.integration
def test_the_script_allows_a_start_with_room_and_exits_zero() -> None:
    stub = WipStub()
    stub.in_review(1)
    stub.in_review(2)
    stub.in_progress(3)
    with serve(stub):
        result = run_script(stub)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "wip-gate: start allowed" in result.stdout


@pytest.mark.integration
def test_the_script_fails_closed_when_github_cannot_be_read() -> None:
    stub = WipStub(fail_status=500)
    with serve(stub):
        result = run_script(stub)
    assert result.returncode == 2
    assert "wip-gate: unknown" in result.stdout


@pytest.mark.integration
def test_bad_limits_are_refused_as_unknown() -> None:
    stub = WipStub()
    with serve(stub):
        result = run_script(stub, "--limits", "4,3")
    assert result.returncode == 2
    assert "wip-gate: unknown" in result.stdout
