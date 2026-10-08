"""The PR change set: what the PR head adds on top of its merge base with the base branch
(CI-POLICY-BASE; used by check_test_immutability.py and check_pr_size.py).

Pass the base *branch* (`origin/main`), never the event's `pull_request.base.sha`: that SHA is
frozen when the event fires, while the checked-out merge ref may already sit on a newer `main`,
so a stale base blames `main`'s later changes on the PR (CI run 37739461709).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class ChangeSetError(Exception):
    """The change set cannot be computed; policy checks fail closed on it."""


@dataclass(frozen=True)
class ChangeSet:
    merge_base: str
    head: str
    changes: str  # `git diff` output for merge_base..head

    def describe(self, base: str, head: str) -> str:
        return (
            f"change set {self.merge_base[:12]}..{self.head[:12]} (merge base of {base} and {head})"
        )


def _git(cwd: Path | str | None, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


def _commit(ref: str, cwd: Path | str | None) -> str:
    res = _git(cwd, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if res.returncode != 0:
        raise ChangeSetError(f"{ref} does not name a commit in this checkout")
    return res.stdout.strip()


def merge_base(base: str, head: str, cwd: Path | str | None = None) -> str:
    """Newest commit shared by the base branch and the PR head."""
    base_sha, head_sha = _commit(base, cwd), _commit(head, cwd)
    res = _git(cwd, "merge-base", base_sha, head_sha)
    if res.returncode != 0 or not res.stdout.strip():
        raise ChangeSetError(f"{base} and {head} have no merge base")
    return res.stdout.strip()


def diff(base: str, head: str, *options: str, cwd: Path | str | None = None) -> ChangeSet:
    """`git diff <options> <merge base>..<head>`: the PR's own changes only."""
    mb = merge_base(base, head, cwd)
    head_sha = _commit(head, cwd)
    res = _git(cwd, "diff", *options, mb, head_sha)
    if res.returncode != 0:
        raise ChangeSetError(f"git diff failed:\n{res.stderr}")
    return ChangeSet(merge_base=mb, head=head_sha, changes=res.stdout)
