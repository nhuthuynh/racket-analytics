"""ST-003: CI fails a PR that modifies or deletes accepted tests or gold data unless the
senior-qa-engineer applied the `qa-approved-test-change` label [EP/ENG-28, NFR-078]."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit

GUARD = SCRIPTS_DIR / "ci" / "check_test_immutability.py"
LABEL = "qa-approved-test-change"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
        },
    ).stdout.strip()


def write(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "r"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    write(r, "backend/tests/unit/test_a.py", "def test_a():\n    assert 1 == 1\n")
    write(r, "web/e2e/journey.spec.ts", "test('x', () => {})\n")
    write(r, "fixtures/gold/set1/labels.json", "{}\n")
    write(r, "tests/features/x.feature", "Feature: x\n")
    write(r, "backend/src/app.py", "x = 1\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "base")
    git(r, "checkout", "-q", "-b", "pr")
    return r


def commit(repo: Path) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "change", "--allow-empty")


def run_guard(repo: Path, labels: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PR_LABELS"] = json.dumps(labels or [])
    return subprocess.run(
        ["python3", str(GUARD), "--base", "main", "--head", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


# ---------------------------------------------------------------- negative cases first
@pytest.mark.parametrize(
    "rel",
    [
        "backend/tests/unit/test_a.py",
        "web/e2e/journey.spec.ts",
        "fixtures/gold/set1/labels.json",
        "tests/features/x.feature",
    ],
)
def test_modifying_a_protected_file_fails(repo: Path, rel: str) -> None:
    write(repo, rel, "weakened\n")
    commit(repo)
    res = run_guard(repo)
    assert res.returncode == 1
    assert rel in res.stdout
    assert LABEL in res.stdout


def test_deleting_a_protected_file_fails(repo: Path) -> None:
    (repo / "backend/tests/unit/test_a.py").unlink()
    commit(repo)
    res = run_guard(repo)
    assert res.returncode == 1
    assert "deleted" in res.stdout


def test_renaming_a_protected_file_fails(repo: Path) -> None:
    git(repo, "mv", "backend/tests/unit/test_a.py", "backend/tests/unit/test_b.py")
    commit(repo)
    res = run_guard(repo)
    assert res.returncode == 1
    assert "backend/tests/unit/test_a.py" in res.stdout


def test_moving_a_test_out_of_the_protected_tree_fails(repo: Path) -> None:
    git(repo, "mv", "backend/tests/unit/test_a.py", "backend/test_a.py")
    commit(repo)
    assert run_guard(repo).returncode == 1


def test_a_different_label_does_not_approve(repo: Path) -> None:
    write(repo, "backend/tests/unit/test_a.py", "weakened\n")
    commit(repo)
    assert run_guard(repo, ["lgtm", "qa-approved"]).returncode == 1


def test_bad_base_ref_fails_closed(repo: Path) -> None:
    env = dict(os.environ, PR_LABELS="[]")
    res = subprocess.run(
        ["python3", str(GUARD), "--base", "does-not-exist", "--head", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert res.returncode == 2


def test_malformed_labels_fail_closed(repo: Path) -> None:
    write(repo, "backend/tests/unit/test_a.py", "weakened\n")
    commit(repo)
    env = dict(os.environ, PR_LABELS="not json")
    res = subprocess.run(
        ["python3", str(GUARD), "--base", "main", "--head", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert res.returncode != 0


# ---------------------------------------------------------------- allowed changes
def test_adding_new_tests_passes(repo: Path) -> None:
    write(repo, "backend/tests/unit/test_new.py", "def test_new():\n    assert True\n")
    write(repo, "fixtures/gold/set2/labels.json", "{}\n")
    commit(repo)
    res = run_guard(repo)
    assert res.returncode == 0, res.stdout


def test_changing_production_code_passes(repo: Path) -> None:
    write(repo, "backend/src/app.py", "x = 2\n")
    commit(repo)
    assert run_guard(repo).returncode == 0


def test_qa_label_approves_a_protected_change(repo: Path) -> None:
    write(repo, "backend/tests/unit/test_a.py", "def test_a():\n    assert 2 == 2\n")
    commit(repo)
    res = run_guard(repo, [LABEL])
    assert res.returncode == 0
    assert "approved" in res.stdout


def test_only_changes_since_the_merge_base_count(repo: Path) -> None:
    # main moves on and edits a test (already reviewed there); the PR branch must not be blamed.
    git(repo, "checkout", "-q", "main")
    write(repo, "backend/tests/unit/test_a.py", "def test_a():\n    assert 3 == 3\n")
    commit(repo)
    git(repo, "checkout", "-q", "pr")
    write(repo, "backend/src/app.py", "x = 3\n")
    commit(repo)
    assert run_guard(repo).returncode == 0
