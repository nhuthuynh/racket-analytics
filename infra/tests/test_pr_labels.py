"""CI-POLICY-LIVE-LABELS: `scripts/ci/pr_labels.py` gives the PR policy the PR's labels as they
are when the check runs (GET /repos/{repo}/issues/{pr}/labels), not as the triggering event froze
them. When the API cannot answer, the caller keeps the event payload, and the log says which
source was used. Unit tests call the helper against github_stub over a real socket; the scripts
run as ci.yml runs them in test_pr_policy_live_labels_scenarios.py. Negative cases first.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Iterator
from types import ModuleType

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR
from github_stub import PR_NUMBER, REPO, GitHubStub, serve

pytestmark = pytest.mark.unit
CI = SCRIPTS_DIR / "ci"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pr_labels", CI / "pr_labels.py")
    assert spec, "scripts/ci/pr_labels.py is missing"
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def github() -> Iterator[GitHubStub]:
    with serve(GitHubStub(page_size=2)) as stub:
        yield stub


def env_for(stub: GitHubStub, **extra: str) -> dict[str, str]:
    return {
        "GITHUB_API_URL": stub.url,
        "GITHUB_REPOSITORY": REPO,
        "GITHUB_TOKEN": "t0k",
        "PR_NUMBER": str(PR_NUMBER),
        **extra,
    }


# ------------------------------------------------------------------------- helper (unit)
def test_api_failure_falls_back_to_the_payload(
    github: GitHubStub, capsys: pytest.CaptureFixture[str]
) -> None:
    github.labels, github.labels_status = ["size-waiver"], 500
    assert load().live_labels(env_for(github), "pr-size") is None
    assert "pr-size: labels from the event payload (GitHub API failed:" in capsys.readouterr().out


def test_unreachable_api_falls_back(capsys: pytest.CaptureFixture[str]) -> None:
    env = {"GITHUB_API_URL": "http://127.0.0.1:9", "GITHUB_REPOSITORY": REPO}
    assert load().live_labels(env | {"GITHUB_TOKEN": "t", "PR_NUMBER": "7"}, "x") is None
    assert "x: labels from the event payload (GitHub API failed:" in capsys.readouterr().out


def test_endless_pagination_falls_back(github: GitHubStub) -> None:
    github.labels = ["size-waiver"]
    github.page_size = 0  # the stub then answers with an empty page and a next link forever
    assert load().live_labels(env_for(github), "x") is None
    assert len(github.requests) == 10  # bounded: GitHub allows at most 100 labels per PR


@pytest.mark.parametrize("missing", ["GITHUB_TOKEN", "PR_NUMBER", "GITHUB_REPOSITORY"])
def test_no_token_or_pr_falls_back_without_calling_the_api(
    github: GitHubStub, missing: str, capsys: pytest.CaptureFixture[str]
) -> None:
    env = env_for(github)
    del env[missing]
    assert load().live_labels(env, "x") is None
    assert github.requests == []
    assert f"x: labels from the event payload (no {missing})" in capsys.readouterr().out


def test_api_labels_win_over_a_stale_payload(
    github: GitHubStub, capsys: pytest.CaptureFixture[str]
) -> None:
    github.labels = ["triage", "docs", "size-waiver"]  # 2 pages at page_size=2
    env = env_for(github, PR_LABELS="[]")
    assert load().live_labels(env, "pr-size") == ["triage", "docs", "size-waiver"]
    paths = [p for p, _ in github.requests]
    assert paths[0] == f"/repos/{REPO}/issues/{PR_NUMBER}/labels?per_page=100"
    assert len(paths) == 2
    assert {a for _, a in github.requests} == {"Bearer t0k"}
    out = capsys.readouterr().out
    assert "pr-size: labels from the GitHub API: triage, docs, size-waiver" in out


# --------------------------------------------------------------------------- ci.yml wiring
def test_pr_policy_job_reads_labels_live_with_least_privilege() -> None:
    wf = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    types = wf[True]["pull_request"]["types"]  # PyYAML reads the bare `on:` key as True
    assert {"labeled", "unlabeled"} <= set(types)
    job = wf["jobs"]["pr-policy"]
    assert job["permissions"] == {"contents": "read", "pull-requests": "read", "issues": "read"}
    for step in (s for s in job["steps"] if "run" in s):
        assert step["env"]["GITHUB_TOKEN"] == "${{ github.token }}", step["name"]
        assert step["env"]["PR_NUMBER"] == "${{ github.event.pull_request.number }}", step["name"]
