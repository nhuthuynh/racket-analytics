"""CI-POLICY-BASE: the PR-policy job judges only the PR's own change set (EP/ENG-28, NFR-078;
EP/ENG-04, NFR-077).

Incident: CI run 37739461709 (job 113186548205, PR #6, docs only) failed test immutability on
`web/e2e/sprint-01/resumable-upload.spec.ts`. PR #9 had changed that spec on `main` 11 s before
the run. The job diffed `github.event.pull_request.base.sha...HEAD`; `HEAD` is the PR merge ref,
which GitHub had already rebuilt on the newer `main`, so the stale event base blamed `main`'s
change on the PR.

The integration tests below rebuild that situation with real git: an `origin` remote, a PR
branch, `main` moving after the event, and the runner's checkout of the merge ref with full
history (`fetch-depth: 0`). They then run the `pr-policy` steps exactly as written in
`.github/workflows/ci.yml`, with each `${{ ... }}` expression filled in from the event.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
IMMUTABILITY_STEP = "Test and gold immutability (EP/ENG-28, NFR-078)"
SIZE_STEP = "PR size (EP/ENG-04)"
MOVED_SPEC = "web/e2e/sprint-01/resumable-upload.spec.ts"
EXPRESSION = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **GIT_ENV},
    ).stdout.strip()


def write(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def lines(n: int) -> str:
    return "".join(f"line {i}\n" for i in range(n))


@dataclass
class PullRequest:
    """A PR as GitHub sees it: an origin remote, the event payload and the runner checkout."""

    root: Path
    labels: list[str] = field(default_factory=list)
    base_sha: str = ""  # github.event.pull_request.base.sha, frozen when the event fired
    head_sha: str = ""

    @property
    def origin(self) -> Path:
        return self.root / "origin.git"

    @property
    def dev(self) -> Path:
        return self.root / "dev"

    @property
    def runner(self) -> Path:
        return self.root / "runner"

    def change_in_pr(self, rel: str, text: str) -> None:
        write(self.dev, rel, text)
        git(self.dev, "add", "-A")
        git(self.dev, "commit", "-q", "-m", f"pr: {rel}")
        git(self.dev, "push", "-q", "origin", "pr")

    def open_event(self) -> None:
        """The `pull_request` event fires: GitHub freezes base.sha and head.sha."""
        self.base_sha = git(self.dev, "rev-parse", "origin/main")
        self.head_sha = git(self.dev, "rev-parse", "pr")

    def main_moves(self, rel: str, text: str) -> None:
        """Another PR merges into main after the event (PR #9 in the incident)."""
        git(self.dev, "checkout", "-q", "main")
        write(self.dev, rel, text)
        git(self.dev, "add", "-A")
        git(self.dev, "commit", "-q", "-m", f"main: {rel}")
        git(self.dev, "push", "-q", "origin", "main")
        git(self.dev, "checkout", "-q", "pr")

    def checkout_merge_ref(self) -> str:
        """actions/checkout with fetch-depth 0 on the merge ref GitHub rebuilt on current main."""
        self.runner.mkdir()
        git(self.runner, "init", "-q")
        git(self.runner, "remote", "add", "origin", str(self.origin))
        git(self.runner, "fetch", "-q", "origin", "+refs/heads/*:refs/remotes/origin/*")
        git(self.runner, "checkout", "-q", "--detach", "origin/main")
        git(self.runner, "merge", "-q", "--no-ff", "--no-edit", self.head_sha)
        # The step commands call scripts/ci/... relative to the checkout.
        (self.runner / "scripts").symlink_to(SCRIPTS_DIR, target_is_directory=True)
        return git(self.runner, "rev-parse", "HEAD")

    def context(self, merge_sha: str) -> dict[str, str]:
        return {
            "toJSON(github.event.pull_request.labels.*.name)": json.dumps(self.labels),
            "github.event.pull_request.base.sha": self.base_sha,
            "github.event.pull_request.head.sha": self.head_sha,
            "github.event.pull_request.base.ref": "main",
            "github.base_ref": "main",
            "github.head_ref": "pr",
            "github.sha": merge_sha,
        }


@pytest.fixture
def pr(tmp_path: Path) -> PullRequest:
    p = PullRequest(root=tmp_path)
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(p.origin))
    git(tmp_path, "clone", "-q", str(p.origin), str(p.dev))
    git(p.dev, "checkout", "-q", "-b", "main")
    write(p.dev, MOVED_SPEC, "test('resume', () => {})\n")
    write(p.dev, "backend/tests/unit/test_a.py", "def test_a():\n    assert 1 == 1\n")
    write(p.dev, "backend/src/app.py", "x = 1\n")
    write(p.dev, "docs/notes.md", "# notes\n")
    git(p.dev, "add", "-A")
    git(p.dev, "commit", "-q", "-m", "base")
    git(p.dev, "push", "-q", "origin", "main")
    git(p.dev, "checkout", "-q", "-b", "pr")
    return p


def pr_policy_steps() -> list[dict]:
    return list(yaml.safe_load(WORKFLOW.read_text())["jobs"]["pr-policy"]["steps"])


def run_step(name: str, pr: PullRequest, merge_sha: str) -> subprocess.CompletedProcess[str]:
    """Run one pr-policy step as the runner does: env resolved from the event, `run` in bash."""
    (step,) = [s for s in pr_policy_steps() if s.get("name") == name]
    ctx = pr.context(merge_sha)
    assert not EXPRESSION.search(step["run"]), "expressions belong in env, not in run (injection)"

    def resolve(value: str) -> str:
        def one(m: re.Match[str]) -> str:
            expr = m.group(1)
            if expr not in ctx:
                pytest.fail(f"{name}: expression not modelled by this test: {expr}")
            return ctx[expr]

        return EXPRESSION.sub(one, str(value))

    env = {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")}
    env.update(GIT_ENV)
    env.update({k: resolve(v) for k, v in (step.get("env") or {}).items()})
    return subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=pr.runner,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


# ---------------------------------------------------------------- negative cases first
@pytest.mark.integration
def test_a_docs_only_pr_is_not_blamed_for_a_test_edit_that_reached_main_after_the_event(
    pr: PullRequest,
) -> None:
    pr.change_in_pr("docs/notes.md", "# notes\n\nmore\n")
    pr.open_event()
    pr.main_moves(MOVED_SPEC, "test('resume', () => { /* hold one chunk */ })\n")
    merge_sha = pr.checkout_merge_ref()

    res = run_step(IMMUTABILITY_STEP, pr, merge_sha)

    assert res.returncode == 0, res.stdout + res.stderr
    assert MOVED_SPEC not in res.stdout


@pytest.mark.integration
def test_a_small_pr_is_not_blamed_for_lines_that_reached_main_after_the_event(
    pr: PullRequest,
) -> None:
    pr.change_in_pr("docs/change.md", lines(10))
    pr.open_event()
    pr.main_moves("backend/src/big.py", lines(450))
    merge_sha = pr.checkout_merge_ref()

    res = run_step(SIZE_STEP, pr, merge_sha)

    assert res.returncode == 0, res.stdout + res.stderr
    assert "pr-size: 10 changed lines" in res.stdout


@pytest.mark.integration
@pytest.mark.parametrize("step", [IMMUTABILITY_STEP, SIZE_STEP])
def test_a_missing_base_branch_fails_closed(pr: PullRequest, step: str) -> None:
    pr.change_in_pr("docs/notes.md", "# notes\n\nmore\n")
    pr.open_event()
    merge_sha = pr.checkout_merge_ref()
    git(pr.runner, "update-ref", "-d", "refs/remotes/origin/main")

    res = run_step(step, pr, merge_sha)

    assert res.returncode == 2, res.stdout + res.stderr


# ---------------------------------------------------------------- positive controls
@pytest.mark.integration
def test_a_test_edit_in_the_pr_is_still_caught_when_main_moved(pr: PullRequest) -> None:
    pr.change_in_pr("backend/tests/unit/test_a.py", "def test_a():\n    pass\n")
    pr.open_event()
    pr.main_moves(MOVED_SPEC, "test('resume', () => { /* hold one chunk */ })\n")
    merge_sha = pr.checkout_merge_ref()

    res = run_step(IMMUTABILITY_STEP, pr, merge_sha)

    assert res.returncode == 1, res.stdout + res.stderr
    assert "modified: backend/tests/unit/test_a.py" in res.stdout
    assert MOVED_SPEC not in res.stdout


@pytest.mark.integration
def test_an_oversize_pr_still_fails_when_main_moved(pr: PullRequest) -> None:
    pr.change_in_pr("backend/src/big.py", lines(401))
    pr.open_event()
    pr.main_moves("docs/notes.md", lines(30))
    merge_sha = pr.checkout_merge_ref()

    res = run_step(SIZE_STEP, pr, merge_sha)

    assert res.returncode == 1, res.stdout + res.stderr
    assert "pr-size: 401 changed lines" in res.stdout


@pytest.mark.integration
def test_without_a_moving_main_the_gate_is_unchanged(pr: PullRequest) -> None:
    pr.change_in_pr(MOVED_SPEC, "test('resume', () => { /* weakened */ })\n")
    pr.open_event()
    merge_sha = pr.checkout_merge_ref()

    res = run_step(IMMUTABILITY_STEP, pr, merge_sha)

    assert res.returncode == 1, res.stdout + res.stderr
    assert f"modified: {MOVED_SPEC}" in res.stdout


# ---------------------------------------------------------------- workflow wiring (unit)
@pytest.mark.unit
@pytest.mark.parametrize("step", [IMMUTABILITY_STEP, SIZE_STEP])
def test_policy_steps_never_diff_against_the_event_base_sha(step: str) -> None:
    (s,) = [x for x in pr_policy_steps() if x.get("name") == step]
    text = json.dumps(s)
    assert "pull_request.base.sha" not in text
    assert "github.base_ref" in text
