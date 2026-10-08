"""A pull request as the `pr-policy` job sees it, rebuilt with real git (CI-POLICY-BASE).

`origin`, the event's frozen base/head SHAs, `main` moving after the event, and the runner's
fetch-depth-0 checkout of the merge ref rebuilt on the current `main`. `run_policy` runs the
`pr-policy` steps of ci.yml verbatim, each `${{ ... }}` in `env` filled in from the event.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR

IMMUTABILITY_STEP = "Test and gold immutability (EP/ENG-28, NFR-078)"
SIZE_STEP = "PR size (EP/ENG-04)"
E2E_SPEC = "web/e2e/sprint-01/resumable-upload.spec.ts"
UNIT_TEST = "backend/tests/unit/test_a.py"
EXPRESSION = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")
GIT_ENV = {
    **{
        f"GIT_{who}_{what}": v
        for who in ("AUTHOR", "COMMITTER")
        for what, v in (("NAME", "t"), ("EMAIL", "t@example.invalid"))
    },
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, **GIT_ENV}
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env
    ).stdout.strip()


def commit(repo: Path, rel: str, text: str) -> None:
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", rel)


def lines(n: int) -> str:
    return "".join(f"line {i}\n" for i in range(n))


@dataclass
class PullRequest:
    root: Path
    base_sha: str = ""  # github.event.pull_request.base.sha, frozen when the event fired
    head_sha: str = ""

    @classmethod
    def opened_against_main(cls, root: Path) -> PullRequest:
        p = cls(root)
        git(root, "init", "-q", "--bare", "-b", "main", str(root / "origin.git"))
        git(root, "clone", "-q", str(root / "origin.git"), str(p.dev))
        git(p.dev, "checkout", "-q", "-b", "main")
        commit(p.dev, E2E_SPEC, "test('resume', () => {})\n")
        commit(p.dev, UNIT_TEST, "def test_a():\n    assert 1 == 1\n")
        git(p.dev, "push", "-q", "origin", "main")
        git(p.dev, "checkout", "-q", "-b", "pr")
        return p

    @property
    def dev(self) -> Path:
        return self.root / "dev"

    @property
    def runner(self) -> Path:
        return self.root / "runner"

    def push(self, branch: str, rel: str, text: str) -> None:
        git(self.dev, "checkout", "-q", branch)
        commit(self.dev, rel, text)
        git(self.dev, "push", "-q", "origin", branch)
        git(self.dev, "checkout", "-q", "pr")

    def open_event(self, rel: str, text: str) -> None:
        """The PR changes `rel`, then the event fires and freezes base.sha and head.sha."""
        self.push("pr", rel, text)
        self.base_sha = git(self.dev, "rev-parse", "origin/main")
        self.head_sha = git(self.dev, "rev-parse", "pr")

    def checkout_merge_ref(self) -> None:
        """actions/checkout (fetch-depth 0) of the merge ref GitHub rebuilt on current main."""
        self.runner.mkdir()
        git(self.runner, "init", "-q")
        git(self.runner, "remote", "add", "origin", str(self.root / "origin.git"))
        git(self.runner, "fetch", "-q", "origin", "+refs/heads/*:refs/remotes/origin/*")
        git(self.runner, "checkout", "-q", "--detach", "origin/main")
        git(self.runner, "merge", "-q", "--no-ff", "--no-edit", self.head_sha)
        (self.runner / "scripts").symlink_to(SCRIPTS_DIR, target_is_directory=True)

    def run_policy(self) -> dict[str, subprocess.CompletedProcess[str]]:
        event = {
            "toJSON(github.event.pull_request.labels.*.name)": "[]",
            "github.event.pull_request.base.sha": self.base_sha,
            "github.event.pull_request.head.sha": self.head_sha,
            "github.base_ref": "main",
            "github.sha": git(self.runner, "rev-parse", "HEAD"),
        }
        env = {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")} | GIT_ENV
        results = {}
        for step in policy_steps():
            assert not EXPRESSION.search(step["run"]), "expressions belong in env, not in run"
            step_env = {
                k: EXPRESSION.sub(lambda m: event[m.group(1)], str(v))
                for k, v in step.get("env", {}).items()
            }
            results[step["name"]] = subprocess.run(
                ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
                cwd=self.runner,
                capture_output=True,
                text=True,
                env=env | step_env,
                timeout=60,
                check=False,
            )
        return results


def policy_steps() -> list[dict[str, str]]:
    steps = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())["jobs"]
    return [s for s in steps["pr-policy"]["steps"] if "run" in s]
