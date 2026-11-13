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
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from conftest import SCRIPTS_DIR
from wip_stub import PE, QA, REPO, WipStub, fake_merge_ready, head_of, review, serve, ticket_pr

SCRIPT = SCRIPTS_DIR / "measure" / "wip_gate.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("wip_gate", SCRIPT)
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def counts(stub: WipStub) -> dict[str, int]:
    return load().count_stages(stub.pulls, stub.reviews, stub.merge_ready)


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
    pr: dict[str, Any], reviews: Sequence[dict[str, Any]] = (), merge_ready: bool = False
) -> Any:
    return load().stage_of(pr, list(reviews), merge_ready)


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
    assert stage(ticket_pr(1), [review(PE, old), review(QA, old)], merge_ready=True) == "in review"


@pytest.mark.unit
def test_a_qa_changes_requested_on_the_head_sends_the_pr_back_to_review() -> None:
    reviews = [review(PE, head_of(1)), review(QA, head_of(1), "CHANGES REQUESTED")]
    assert stage(ticket_pr(1), reviews) == "in review"
    assert stage(ticket_pr(1), reviews, merge_ready=True) == "in review"


@pytest.mark.unit
def test_a_pr_merge_ready_on_its_head_awaits_merge() -> None:
    reviews = [review(PE, head_of(1)), review(QA, head_of(1))]
    assert stage(ticket_pr(1), reviews, merge_ready=True) == "awaiting merge"


@pytest.mark.unit
def test_a_tier_0_pr_merge_ready_on_one_approve_awaits_merge() -> None:
    reviews = [review("business-analyst", head_of(1))]
    assert stage(ticket_pr(1), reviews, merge_ready=True) == "awaiting merge"


@pytest.mark.unit
def test_both_approves_that_merge_ready_still_refuses_stay_in_review() -> None:
    # e.g. a tier 2 PR without the security-privacy-engineer verdict, or a red ci-gate
    # (live 2026-11-13: #239 and #220 had both approves and merge_ready.py rc 1).
    reviews = [review(PE, head_of(1)), review(QA, head_of(1))]
    assert stage(ticket_pr(1), reviews, merge_ready=False) == "in review"


@pytest.mark.unit
def test_merge_ready_is_asked_only_with_an_approve_and_no_changes_on_the_head() -> None:
    wg = load()
    sha = head_of(1)
    assert not wg.merge_candidate(ticket_pr(1), [])
    assert not wg.merge_candidate(ticket_pr(1, draft=True), [review(PE, sha)])
    assert not wg.merge_candidate(ticket_pr(1), [review(PE, "f" * 40)])
    assert not wg.merge_candidate(
        ticket_pr(1), [review(PE, sha), review(QA, sha, "CHANGES REQUESTED")]
    )
    assert wg.merge_candidate(ticket_pr(1), [review("business-analyst", sha)])


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


def run_script(
    stub: WipStub, tmp_path: Path, *extra: str, rc: int | None = None
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in {"GITHUB_TOKEN", "GH_TOKEN"}}
    env["GITHUB_API_URL"] = stub.url
    fake = fake_merge_ready(tmp_path, stub.merge_ready, rc)
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            REPO,
            "--stage",
            "start",
            "--merge-ready",
            str(fake),
            *extra,
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


@pytest.mark.integration
def test_the_script_refuses_a_fourth_start_over_rest_and_names_the_stage(tmp_path: Path) -> None:
    stub = WipStub()
    for n in (1, 2, 3):
        stub.in_review(n)
    with serve(stub):
        result = run_script(stub, tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "In progress 0 · in review 3 · awaiting QA 0 · awaiting merge 0" in result.stdout
    assert "wip-gate: start refused: in review 3 of 3" in result.stdout
    # REST only, paged past the end (two items a page): no GraphQL, no Link header.
    assert all(r.startswith(f"/repos/{REPO}/") for r in stub.requests), stub.requests
    assert any("page=3" in r for r in stub.requests if "/pulls?" in r)


@pytest.mark.integration
def test_awaiting_merge_is_what_merge_ready_says_on_the_head(tmp_path: Path) -> None:
    stub = WipStub()
    stub.awaiting_merge(7)
    stub.in_progress(8)
    stub.awaiting_qa(9)  # an approve on the head: merge_ready.py is asked and says no
    stub.in_review(10)  # no approve: merge_ready.py is not asked
    with serve(stub):
        result = run_script(stub, tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "In progress 1 · in review 1 · awaiting QA 1 · awaiting merge 1" in result.stdout
    assert "awaiting merge 1 of 1" in result.stdout
    assert any(r.startswith(f"/repos/{REPO}/pulls/7/reviews") for r in stub.requests)
    calls = (tmp_path / "calls.log").read_text().splitlines()
    assert sorted(calls) == [
        f"--repo {REPO} --pr 7 --sha {head_of(7)}",
        f"--repo {REPO} --pr 9 --sha {head_of(9)}",
    ]


@pytest.mark.integration
def test_the_script_fails_closed_when_merge_ready_cannot_answer(tmp_path: Path) -> None:
    stub = WipStub()
    stub.awaiting_merge(7)
    with serve(stub):
        result = run_script(stub, tmp_path, rc=2)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "wip-gate: unknown" in result.stdout


@pytest.mark.integration
def test_the_script_allows_a_start_with_room_and_exits_zero(tmp_path: Path) -> None:
    stub = WipStub()
    stub.in_review(1)
    stub.in_review(2)
    stub.in_progress(3)
    with serve(stub):
        result = run_script(stub, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "wip-gate: start allowed" in result.stdout


@pytest.mark.integration
def test_the_script_fails_closed_when_github_cannot_be_read(tmp_path: Path) -> None:
    stub = WipStub(fail_status=500)
    with serve(stub):
        result = run_script(stub, tmp_path)
    assert result.returncode == 2
    assert "wip-gate: unknown" in result.stdout


@pytest.mark.integration
def test_bad_limits_are_refused_as_unknown(tmp_path: Path) -> None:
    stub = WipStub()
    with serve(stub):
        result = run_script(stub, tmp_path, "--limits", "4,3")
    assert result.returncode == 2
    assert "wip-gate: unknown" in result.stdout
