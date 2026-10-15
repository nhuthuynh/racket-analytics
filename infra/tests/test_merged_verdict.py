"""FIX-03-2b (goal metric G03-12-PE-PR24-01; ledger row PE-PR24-01): `scripts/measure/
merged_verdict.py` says whether a role's latest verdict on a MERGED pull request is
"Verdict: APPROVE" on the head it was merged at.

Root cause of PE-PR24-01: PR #24 merged at `898883b` while `merge_ready.py` (on main since
PR #5) would have refused it; nothing checked a merged PR afterwards, so the miss surfaced only
in a manual audit (PE-R3S3-04 F1). This check is the post-merge read of the same verdict rule.

Unit tests drive the pure `merged_reasons()` rule; integration tests run the script over HTTP
against the local GitHub API stub. Negative cases first.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from types import ModuleType
from typing import Any

import pytest
from conftest import SCRIPTS_DIR
from github_stub import HEAD_SHA, OLD_SHA, PR_NUMBER, REPO, GitHubStub, review, serve

SCRIPT = SCRIPTS_DIR / "measure" / "merged_verdict.py"
PE = "principal-engineer"
OTHER_SHA = "c3" * 20
LATER = "2026-10-15T10:00:00Z"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("merged_verdict", SCRIPT)
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def merged_pr(sha: str = HEAD_SHA, merged: bool = True) -> dict[str, Any]:
    return {
        "number": PR_NUMBER,
        "state": "closed" if merged else "open",
        "merged": merged,
        "merged_at": "2026-10-08T20:13:21Z" if merged else None,
        "head": {"sha": sha},
        "base": {"ref": "main"},
    }


def pending(sha: str = OTHER_SHA, review_id: int = 9) -> dict[str, Any]:
    """The token owner's own unsubmitted review: listed, no body, no submitted_at."""
    return {
        "id": review_id,
        "user": {"login": "nhuthuynh"},
        "author_association": "OWNER",
        "state": "PENDING",
        "commit_id": sha,
    }


def pr24_reviews() -> list[dict[str, Any]]:
    """PR #24 as GitHub lists it: both reviewers asked for changes on an earlier head,
    and an empty pending review sits on another commit."""
    return [
        pending(),
        review(PE, "CHANGES REQUESTED", OLD_SHA, 1),
        review("senior-qa-engineer", "CHANGES REQUESTED", OLD_SHA, 2),
    ]


def reasons(pr: dict[str, Any], reviews: list[dict[str, Any]], roles: tuple[str, ...] = (PE,)):
    return load().merged_reasons(pr, reviews, roles)


# ======================================================================= unit: not met
@pytest.mark.unit
def test_pr24_shape_is_not_met_for_the_principal_engineer() -> None:
    found = reasons(merged_pr(), pr24_reviews())
    assert len(found) == 1
    assert PE in found[0]
    assert "CHANGES REQUESTED" in found[0]


@pytest.mark.unit
def test_no_verdict_at_all_is_not_met() -> None:
    found = reasons(merged_pr(), [pending()])
    assert found == [f"{PE}: no verdict review on PR #{PR_NUMBER}"]


@pytest.mark.unit
def test_an_approval_on_an_earlier_commit_is_not_met() -> None:
    found = reasons(merged_pr(), [review(PE, "APPROVE", OLD_SHA, 1)])
    assert len(found) == 1
    assert OLD_SHA in found[0]


@pytest.mark.unit
def test_a_later_changes_requested_on_the_head_overrides_an_approval() -> None:
    reviews = [
        review(PE, "APPROVE", HEAD_SHA, 1),
        review(PE, "CHANGES REQUESTED", HEAD_SHA, 2, LATER),
    ]
    assert len(reasons(merged_pr(), reviews)) == 1


@pytest.mark.unit
def test_an_outsiders_approval_does_not_count() -> None:
    reviews = [review(PE, "APPROVE", HEAD_SHA, 1, association="NONE")]
    assert len(reasons(merged_pr(), reviews)) == 1


@pytest.mark.unit
def test_a_pull_request_that_is_not_merged_is_not_met() -> None:
    found = reasons(merged_pr(merged=False), [review(PE, "APPROVE", HEAD_SHA, 1)])
    assert found == [f"PR #{PR_NUMBER} is not merged (state open)"]


@pytest.mark.unit
def test_every_role_asked_for_is_checked() -> None:
    reviews = [*pr24_reviews(), review(PE, "APPROVE", HEAD_SHA, 3, LATER)]
    found = reasons(merged_pr(), reviews, (PE, "senior-qa-engineer"))
    assert len(found) == 1
    assert found[0].startswith("senior-qa-engineer:")


# ======================================================================= unit: met
@pytest.mark.unit
def test_an_approval_on_the_merged_head_after_the_merge_is_met() -> None:
    reviews = [*pr24_reviews(), review(PE, "APPROVE", HEAD_SHA, 3, LATER)]
    assert reasons(merged_pr(), reviews) == []


# ======================================================================= integration (HTTP)
def run_script(stub: GitHubStub, *roles: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in {"GITHUB_TOKEN", "GH_TOKEN"}}
    env["GITHUB_API_URL"] = stub.url
    role_args = [arg for role in roles or (PE,) for arg in ("--role", role)]
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", REPO, "--pr", str(PR_NUMBER), *role_args],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )


@pytest.mark.integration
def test_script_refuses_the_pr24_shape_over_http() -> None:
    with serve(GitHubStub(pr=merged_pr(), reviews=pr24_reviews())) as stub:
        result = run_script(stub)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "merged-verdict: not met" in result.stdout
    assert PE in result.stdout


@pytest.mark.integration
def test_script_fails_closed_when_github_cannot_be_read() -> None:
    with serve(GitHubStub(pr=merged_pr(), raw_pr=b"not json")) as stub:
        result = run_script(stub)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "merged-verdict: unknown" in result.stdout


@pytest.mark.integration
def test_script_meets_an_approval_on_the_merged_head_across_pages() -> None:
    reviews = [*pr24_reviews(), review(PE, "APPROVE", HEAD_SHA, 3, LATER)]
    with serve(GitHubStub(pr=merged_pr(), reviews=reviews, page_size=1)) as stub:
        result = run_script(stub)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"merged-verdict: met (PR #{PR_NUMBER} merged head {HEAD_SHA})" in result.stdout
