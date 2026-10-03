"""ST-002/ST-003: workflow structure guards (actionlint validates syntax and shell)."""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

WF = REPO_ROOT / ".github" / "workflows"


def load(name: str) -> dict:
    return yaml.safe_load((WF / name).read_text())


@pytest.mark.skipif(shutil.which("actionlint") is None, reason="actionlint not installed")
def test_actionlint_passes_on_every_workflow() -> None:
    res = subprocess.run(
        ["actionlint", "-color=false"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stdout + res.stderr


def test_ci_gate_needs_every_per_pr_job() -> None:
    jobs = load("ci.yml")["jobs"]
    nightly_only = {"flaky-report"}
    expected = set(jobs) - {"ci-gate"} - nightly_only
    assert set(jobs["ci-gate"]["needs"]) == expected
    assert jobs["ci-gate"]["if"] == "always()"


def test_every_third_party_action_is_pinned_to_a_commit_sha() -> None:
    for wf in WF.glob("*.yml"):
        for m in re.finditer(r"uses:\s*([^\s#]+)", wf.read_text()):
            ref = m.group(1)
            if ref.startswith("./"):
                continue
            assert re.search(r"@[0-9a-f]{40}$", ref), f"{wf.name}: {ref}"


def test_default_token_permissions_are_read_only_or_none() -> None:
    assert load("ci.yml")["permissions"] == {"contents": "read"}
    assert load("claude-review.yml")["permissions"] == {}


def test_every_job_has_a_timeout() -> None:
    for wf in WF.glob("*.yml"):
        for name, job in load(wf.name)["jobs"].items():
            assert "timeout-minutes" in job, f"{wf.name}:{name}"


def test_claude_review_is_guarded_against_bots_forks_and_runaway_runs() -> None:
    doc = load("claude-review.yml")
    job = doc["jobs"]["review"]
    assert "user.type != 'Bot'" in job["if"]
    assert "head.repo.full_name == github.repository" in job["if"]
    assert job["permissions"] == {"contents": "read", "pull-requests": "write", "issues": "read"}
    assert doc["concurrency"]["cancel-in-progress"] is True
    step = next(s for s in job["steps"] if "claude-code-action" in s.get("uses", ""))
    assert "--max-turns" in step["with"]["claude_args"]
    assert "secrets.ANTHROPIC_API_KEY" in step["with"]["anthropic_api_key"]


def test_test_immutability_guard_reruns_when_labels_change() -> None:
    on = load("ci.yml")[True]  # PyYAML reads the `on:` key as boolean True
    assert {"labeled", "unlabeled"} <= set(on["pull_request"]["types"])
