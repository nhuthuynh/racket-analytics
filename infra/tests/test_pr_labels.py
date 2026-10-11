"""CI-POLICY-LIVE-LABELS: `scripts/ci/pr_labels.py` gives the PR policy the PR's labels as they
are when the check runs (GET /repos/{repo}/issues/{pr}/labels), not as the triggering event froze
them. When the API cannot answer, the caller keeps the event payload, and the log says which
source was used. Unit tests call the helper against github_stub over a real socket; the CLI tests
run both policy scripts as ci.yml does. Negative cases first.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
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


def test_gh_token_is_accepted(github: GitHubStub) -> None:
    env = env_for(github)
    env["GH_TOKEN"] = env.pop("GITHUB_TOKEN")
    assert load().live_labels(env, "x") == []


# ------------------------------------------------------------------- both scripts (CLI)
def run(script: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    clean = {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")}
    return subprocess.run(
        [sys.executable, str(CI / script), "--base", "main"],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=clean | env,
        timeout=60,
        check=False,
    )


def git(repo: Path, *args: str) -> None:
    who = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    ident = {"user.name": "t", "user.email": "t@example.invalid"}
    cfg = [a for k, v in ident.items() for a in ("-c", f"{k}={v}")]
    subprocess.run(["git", *cfg, "-C", str(repo), *args], check=True, capture_output=True,
                   env=os.environ | who)  # fmt: skip


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "backend/tests").mkdir(parents=True)
    (tmp_path / "backend/tests/test_a.py").write_text("x = 1\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "checkout", "-q", "-b", "pr")
    (tmp_path / "backend/tests/test_a.py").write_text("x = 2\n")
    (tmp_path / "big.py").write_text("".join(f"l{i}\n" for i in range(401)))
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "pr")
    return tmp_path


def test_a_removed_label_fails_both_scripts_despite_the_payload(
    repo: Path, github: GitHubStub
) -> None:
    payload = '["size-waiver", "qa-approved-test-change"]'
    for script in ("check_pr_size.py", "check_test_immutability.py"):
        res = run(script, repo, env_for(github, PR_LABELS=payload))
        assert res.returncode == 1, res.stdout
        assert "labels from the GitHub API" in res.stdout


def test_labels_applied_after_the_push_pass_both_scripts(repo: Path, github: GitHubStub) -> None:
    github.labels = ["size-waiver", "qa-approved-test-change"]
    for script in ("check_pr_size.py", "check_test_immutability.py"):
        res = run(script, repo, env_for(github, PR_LABELS="[]"))
        assert res.returncode == 0, res.stdout


def test_bad_payload_still_fails_closed_when_the_api_is_down(
    repo: Path, github: GitHubStub
) -> None:
    github.labels_status = 503
    res = run("check_test_immutability.py", repo, env_for(github, PR_LABELS="not json"))
    assert res.returncode == 2, res.stdout


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
