"""CI run 37732742355 (NFR-056): `gitleaks git .` ran `git log --all` and failed PR #8 on commits
only on other branches. Scan what HEAD puts on main (PR: merge commit); see decision-log."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT

FAKE_KEY = 'key = "%s"\n' % ("q7N2v9Lr4TzX8pWc" + "1HsK6dYb3MfJ0aGe")  # joined: not in git


def gitleaks_command() -> list[str]:
    ci = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())
    runs = "\n".join(s.get("run", "") for s in ci["jobs"]["secrets-and-audit"]["steps"])
    lines = [ln.strip() for ln in runs.splitlines() if ln.strip().startswith("/tmp/gitleaks git")]
    assert len(lines) == 1, lines
    return shlex.split(lines[0])


def log_opts() -> list[str]:
    opts = [a.split("=", 1)[1] for a in gitleaks_command() if a.startswith("--log-opts=")]
    assert opts, "no --log-opts=: gitleaks then runs `git log --all` over every fetched branch"
    return shlex.split(opts[0])


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_the_scan_never_reads_every_fetched_branch() -> None:
    assert not {"--all", "--branches", "--remotes"} & set(log_opts())


@pytest.mark.unit
def test_the_scan_still_fails_the_job_on_a_finding() -> None:
    cmd = gitleaks_command()
    assert cmd[cmd.index("--exit-code") + 1] == "1"
    assert cmd[cmd.index("--config") + 1] == ".gitleaks.toml"


@pytest.mark.unit
def test_the_scan_reads_the_full_history_of_head() -> None:
    assert {"--full-history", "HEAD"} <= set(log_opts())


def _commit(repo: Path, name: str, text: str | None) -> None:
    if text is None:
        (repo / name).unlink()
    else:
        (repo / name).write_text(text)
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", name], check=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """main (clean) -> `other` holds a fake key -> HEAD on a clean `pr` branch off main."""
    shutil.copy(REPO_ROOT / ".gitleaks.toml", tmp_path / ".gitleaks.toml")
    subprocess.run(["git", "init", "-qb", "main", str(tmp_path)], check=True)
    _commit(tmp_path, "readme.txt", "clean\n")
    subprocess.run(["git", "-C", str(tmp_path), "checkout", "-qb", "other"], check=True)
    _commit(tmp_path, "settings.py", FAKE_KEY)
    subprocess.run(["git", "-C", str(tmp_path), "checkout", "-qb", "pr", "main"], check=True)
    _commit(tmp_path, "feature.txt", "clean\n")
    return tmp_path


def _scan(repo: Path) -> subprocess.CompletedProcess[str]:
    cmd = [os.environ["GITLEAKS_BIN"], *gitleaks_command()[1:]]
    return subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=120, check=False)


needs_gitleaks = pytest.mark.skipif(not os.environ.get("GITLEAKS_BIN"), reason="GITLEAKS_BIN")


@pytest.mark.integration
@needs_gitleaks
def test_a_key_committed_on_the_pr_branch_fails_even_if_removed_again(repo: Path) -> None:
    _commit(repo, "leak.py", FAKE_KEY)
    _commit(repo, "leak.py", None)
    res = _scan(repo)
    assert res.returncode == 1, res.stdout + res.stderr


@pytest.mark.integration
@needs_gitleaks
def test_a_key_only_on_another_branch_does_not_fail_this_scan(repo: Path) -> None:
    res = _scan(repo)
    assert res.returncode == 0, res.stdout + res.stderr
