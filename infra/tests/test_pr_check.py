"""CI-FIX-PR-CHECK: scripts/pr-check.sh runs ci.yml's own commands; the Makefile targets and
the pre-push hook's ref rules (the hook runs a recording pr-check here; the real one runs in
test_pr_check_scenarios.py)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR
from pr_checkout import GIT_ENV, git

pytestmark = pytest.mark.unit

PR_CHECK = SCRIPTS_DIR / "pr-check.sh"
HOOK = REPO_ROOT / ".githooks" / "pre-push"
JOBS = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())["jobs"]
ZERO = "0" * 40


def _runs(job: str) -> list[dict[str, str]]:
    return [s for s in JOBS[job]["steps"] if "run" in s]


def test_every_pr_policy_step_runs_with_ci_yml_command_and_name() -> None:
    text = PR_CHECK.read_text()
    steps = _runs("pr-policy")
    assert len(steps) == 5, [s["name"] for s in steps]  # a new pr-policy step needs a row here
    for step in steps:
        assert step["run"].strip() in text, step["run"]
        assert step["name"] in text, step["name"]
    assert 'BASE_REF="main"' in text  # CI's github.base_ref of a PR into main


def test_doc_check_steps_run_with_ci_yml_commands() -> None:
    text = PR_CHECK.read_text()
    runs = [s["run"].strip() for s in _runs("doc-check") if "pip install" not in s["run"]]
    assert len(runs) == 2, runs
    docs = next(r for r in runs if "check_docs.py" in r)
    assert docs.splitlines()[-1].strip() in text  # the diff from BASE_SHA to HEAD
    assert next(r for r in runs if "check_atomic_breakdown.py" in r) in text
    assert JOBS["doc-check"]["name"] in text


def test_ruff_and_unit_commands() -> None:
    text = PR_CHECK.read_text()
    ci = [s["run"] for s in JOBS["python-lint"]["steps"] if "run" in s]
    assert "uv run ruff format --check ." in ci
    assert "uv run ruff format --check ." in text
    assert "uv run ruff check ." in text  # CI adds --output-format=github (annotations only)
    assert "scripts/test-unit.sh" in text
    assert "git fetch origin main" in text


@pytest.mark.parametrize("path", [PR_CHECK, HOOK])
def test_executable(path: Path) -> None:
    assert path.is_file()
    assert os.access(path, os.X_OK), f"{path} is not executable (git update-index --chmod=+x)"


@pytest.mark.parametrize(
    ("target", "says"),
    [("hooks", "git config core.hooksPath .githooks"), ("pr-check", "scripts/pr-check.sh")],
)
def test_make_targets(target: str, says: str) -> None:
    res = subprocess.run(
        ["make", "-n", "-C", str(REPO_ROOT), target], capture_output=True, text=True, check=False
    )
    assert res.returncode == 0, res.stderr
    assert says in res.stdout


def test_unknown_option_is_a_usage_error() -> None:
    res = subprocess.run(["bash", str(PR_CHECK), "--nope"], capture_output=True, text=True)
    assert res.returncode == 2
    assert "usage" in (res.stdout + res.stderr).lower()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A checkout whose scripts/pr-check.sh records its arguments and exits PR_CHECK_RC."""
    git(tmp_path, "init", "-q", "-b", "s06/x")
    (tmp_path / "scripts").mkdir()
    stub = tmp_path / "scripts" / "pr-check.sh"
    stub.write_text('#!/usr/bin/env bash\necho "ran $*" >> "$HOOK_LOG"\nexit "${PR_CHECK_RC:-0}"\n')
    stub.chmod(0o755)
    (tmp_path / "f").write_text("x\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def hook(repo: Path, stdin: str, rc: int = 0) -> tuple[subprocess.CompletedProcess[str], str]:
    log = repo / "hook.log"
    log.write_text("")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")} | GIT_ENV
    env |= {"HOOK_LOG": str(log), "PR_CHECK_RC": str(rc)}
    res = subprocess.run(
        [str(HOOK), "origin", "https://example.invalid/r.git"],
        cwd=repo,
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return res, log.read_text()


def test_hook_runs_pr_check_for_a_ticket_branch_with_its_remote_name(repo: Path) -> None:
    head = git(repo, "rev-parse", "HEAD")
    res, log = hook(repo, f"refs/heads/s06/x {head} refs/heads/s06/x {ZERO}\n")
    assert res.returncode == 0, res.stdout + res.stderr
    assert log == "ran --branch s06/x\n"


def test_hook_blocks_when_pr_check_fails(repo: Path) -> None:
    head = git(repo, "rev-parse", "HEAD")
    res, _ = hook(repo, f"refs/heads/s06/x {head} refs/heads/s06/x {ZERO}\n", rc=1)
    assert res.returncode == 1
    assert "--no-verify" in res.stderr  # names the escape hatch


@pytest.mark.parametrize(
    "remote_ref",
    ["refs/heads/main", "refs/heads/deps/security-audit", "refs/tags/s06/x", "refs/heads/s6/x"],
)
def test_hook_ignores_refs_that_are_not_ticket_branches(repo: Path, remote_ref: str) -> None:
    head = git(repo, "rev-parse", "HEAD")
    res, log = hook(repo, f"refs/heads/s06/x {head} {remote_ref} {ZERO}\n", rc=1)
    assert res.returncode == 0, res.stdout + res.stderr
    assert log == ""


def test_hook_ignores_a_branch_deletion(repo: Path) -> None:
    res, log = hook(repo, f"(delete) {ZERO} refs/heads/s06/x {'a' * 40}\n", rc=1)
    assert res.returncode == 0
    assert log == ""


def test_hook_refuses_a_ticket_push_of_a_commit_that_is_not_checked_out(repo: Path) -> None:
    """pr-check reads the working tree; another commit would be judged on the wrong files."""
    old = git(repo, "rev-parse", "HEAD")
    (repo / "f").write_text("y\n")
    git(repo, "commit", "-q", "-am", "next")
    res, log = hook(repo, f"refs/heads/old {old} refs/heads/s06/old {ZERO}\n")
    assert res.returncode == 1
    assert log == ""
    assert "check out" in res.stderr
