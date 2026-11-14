"""A throwaway checkout for scripts/pr-check.sh and .githooks/pre-push (CI-FIX-PR-CHECK).

A bare `origin` with a `main`, a developer clone on a branch, and the real `scripts/` and
`.githooks/` linked in (git-ignored, so no diff sees them). A recording `uv` stands in for Ruff
and pytest, and a recording `gh` answers the open-PR lookup and `gh auth token`.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from conftest import REPO_ROOT, SCRIPTS_DIR
from pr_checkout import GIT_ENV, git

APP = "backend/src/racket/app.py"
UNIT_TEST = "backend/tests/unit/test_a.py"
BIG = "infra/tool/big.py"  # production code (counted by the size gate), not under red-first paths

UV_STUB = """#!/usr/bin/env bash
printf '%s\\t%s\\n' "$PWD" "$*" >> "$PR_CHECK_STUB_LOG"
exit "${UV_STUB_RC:-0}"
"""
GH_STUB = """#!/usr/bin/env bash
printf 'gh\\t%s\\n' "$*" >> "$PR_CHECK_STUB_LOG"
if [[ "$1 $2" == "auth token" ]]; then echo stub-token; exit 0; fi
if [[ "$1" == api ]]; then cat "$GH_PULLS_JSON"; exit 0; fi
exit 1
"""

# The summary lines pr-check prints, in order: each names the CI job and step it mirrors.
CHECKS = (
    "git fetch origin main",
    "Test and gold immutability (EP/ENG-28, NFR-078)",
    "PR size (EP/ENG-04)",
    "Red first (R3-IN-1, C4-RED)",
    "Decisions findings joined to the ledger (PRC-4.1, PRC-4.2)",
    "Cost per PR table (PRC-11.3)",
    "check_docs.py",
    "check_atomic_breakdown.py",
    "uv run ruff check",
    "uv run ruff format --check .",
    "Unit suites (scripts/test-unit.sh)",
)


@dataclass
class Checkout:
    root: Path
    pulls: list[dict[str, object]] = field(default_factory=list)
    api_url: str = ""

    @classmethod
    def create(cls, root: Path) -> Checkout:
        c = cls(root)
        git(root, "init", "-q", "--bare", "-b", "main", str(c.origin))
        git(root, "clone", "-q", str(c.origin), str(c.dev))
        git(c.dev, "checkout", "-q", "-b", "main")
        for name in ("scripts", ".githooks"):
            (c.dev / name).symlink_to(REPO_ROOT / name, target_is_directory=True)
        with (c.dev / ".git" / "info" / "exclude").open("a") as fh:
            fh.write("scripts\n.githooks\n")
        c.write("README.md", "planted\n")
        c.write("backend/pyproject.toml", "[project]\nname = 'planted'\n")
        c.write(APP, "VALUE = 1\n")
        c.write(UNIT_TEST, "def test_a():\n    assert 1 == 1\n")
        c.commit("chore: base")
        git(c.dev, "push", "-q", "origin", "main")
        c.bin.mkdir()
        for name, text in (("uv", UV_STUB), ("gh", GH_STUB)):
            (c.bin / name).write_text(text)
            (c.bin / name).chmod(0o755)
        c.log.write_text("")
        return c

    @property
    def origin(self) -> Path:
        return self.root / "origin.git"

    @property
    def dev(self) -> Path:
        return self.root / "dev"

    @property
    def bin(self) -> Path:
        return self.root / "bin"

    @property
    def log(self) -> Path:
        return self.root / "stub.log"

    def write(self, rel: str, text: str) -> None:
        (self.dev / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.dev / rel).write_text(text)

    def commit(self, subject: str) -> None:
        git(self.dev, "add", "-A")
        git(self.dev, "commit", "-q", "-m", subject)

    def branch(self, name: str) -> None:
        git(self.dev, "checkout", "-q", "-b", name, "main")

    def env(self) -> dict[str, str]:
        """The developer's shell: no CI or PR variables, the stubs first on PATH."""
        pulls = self.root / "pulls.json"
        pulls.write_text(json.dumps(self.pulls))
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith(("GITHUB_", "PR_", "RA_")) and k not in {"CI", "BASE_REF"}
        }
        env |= GIT_ENV | {
            "PATH": f"{self.bin}{os.pathsep}{env.get('PATH', '')}",
            "PR_CHECK_STUB_LOG": str(self.log),
            "GH_PULLS_JSON": str(pulls),
            "GITHUB_REPOSITORY": "nhuthuynh/racket-analytics",
        }
        if self.api_url:
            env["GITHUB_API_URL"] = self.api_url
        return env

    def pr_check(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPTS_DIR / "pr-check.sh"), *args],
            cwd=self.dev,
            capture_output=True,
            text=True,
            env=self.env(),
            timeout=300,
            check=False,
        )

    def push(self, branch: str, *flags: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "push", *flags, "origin", branch],
            cwd=self.dev,
            capture_output=True,
            text=True,
            env=self.env(),
            timeout=300,
            check=False,
        )

    def stub_calls(self) -> list[str]:
        return self.log.read_text().splitlines()


def summary(out: str) -> list[str]:
    """The PASS/FAIL/SKIP lines after pr-check's summary header."""
    _, sep, tail = out.partition("== pr-check summary")
    assert sep, out[-3000:]
    return [ln for ln in tail.splitlines() if ln.startswith(("PASS ", "FAIL ", "SKIP "))]


def status_of(out: str, step: str) -> str:
    found = [ln.split()[0] for ln in summary(out) if ln.rstrip().endswith(step)]
    assert len(found) == 1, (step, summary(out))
    return found[0]


def lines(n: int) -> str:
    return "".join(f"X{i} = {i}\n" for i in range(n))
