"""A pull request as the `pr-policy` job sees it, rebuilt with real git (CI-POLICY-BASE).

An `origin` remote, the `pull_request` event's frozen base and head SHAs, `main` moving after
the event, and the runner's `actions/checkout` (fetch-depth 0) of the merge ref GitHub rebuilt
on the current `main`. `run_step` then runs a step of `.github/workflows/ci.yml` job
`pr-policy` verbatim, with each `${{ ... }}` in its `env` filled in from that event.
Shared by test_pr_policy_merge_base.py (integration) and test_pr_policy_scenarios.py (Gherkin).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
IMMUTABILITY_STEP = "Test and gold immutability (EP/ENG-28, NFR-078)"
SIZE_STEP = "PR size (EP/ENG-04)"
E2E_SPEC = "web/e2e/sprint-01/resumable-upload.spec.ts"
UNIT_TEST = "backend/tests/unit/test_a.py"
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
    merge_sha: str = ""  # github.sha: the merge ref the runner checked out

    @classmethod
    def opened_against_main(cls, root: Path) -> PullRequest:
        """origin with one commit on main holding accepted tests; a `pr` branch from it."""
        p = cls(root=root)
        git(root, "init", "-q", "--bare", "-b", "main", str(p.origin))
        git(root, "clone", "-q", str(p.origin), str(p.dev))
        git(p.dev, "checkout", "-q", "-b", "main")
        write(p.dev, E2E_SPEC, "test('resume', () => {})\n")
        write(p.dev, UNIT_TEST, "def test_a():\n    assert 1 == 1\n")
        write(p.dev, "backend/src/app.py", "x = 1\n")
        write(p.dev, "docs/notes.md", "# notes\n")
        git(p.dev, "add", "-A")
        git(p.dev, "commit", "-q", "-m", "base")
        git(p.dev, "push", "-q", "origin", "main")
        git(p.dev, "checkout", "-q", "-b", "pr")
        return p

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
        self.merge_sha = git(self.runner, "rev-parse", "HEAD")
        return self.merge_sha

    def context(self) -> dict[str, str]:
        return {
            "toJSON(github.event.pull_request.labels.*.name)": json.dumps(self.labels),
            "github.event.pull_request.base.sha": self.base_sha,
            "github.event.pull_request.head.sha": self.head_sha,
            "github.event.pull_request.base.ref": "main",
            "github.base_ref": "main",
            "github.head_ref": "pr",
            "github.sha": self.merge_sha,
        }


def pr_policy_steps() -> list[dict[str, Any]]:
    return list(yaml.safe_load(WORKFLOW.read_text())["jobs"]["pr-policy"]["steps"])


def run_step(name: str, pr: PullRequest) -> subprocess.CompletedProcess[str]:
    """Run one pr-policy step as the runner does: env resolved from the event, `run` in bash."""
    (step,) = [s for s in pr_policy_steps() if s.get("name") == name]
    ctx = pr.context()
    assert not EXPRESSION.search(step["run"]), "expressions belong in env, not in run (injection)"

    def resolve(value: str) -> str:
        def one(m: re.Match[str]) -> str:
            expr = m.group(1)
            if expr not in ctx:
                raise AssertionError(f"{name}: expression not modelled by this test: {expr}")
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
