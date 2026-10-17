"""IT-04-15 (C4-RED): scripts/ci/check_red_first.py on a throwaway git repo with planted commits.

Real git, the real script, `--base`/`--head` as the pr-policy step passes them. Negative cases
first. The scenario binding (test_red_first_check_scenarios.py) runs the ci.yml step itself.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR
from pr_checkout import GIT_ENV

pytestmark = pytest.mark.integration
SCRIPT = SCRIPTS_DIR / "ci" / "check_red_first.py"


class Repo:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.git("init", "-q", "-b", "main")
        self.commit("chore: base", {"README.md": "base\n", "backend/src/racket/app.py": "x\n"})
        self.base = self.git("rev-parse", "HEAD")
        self.git("checkout", "-q", "-b", "pr")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, **GIT_ENV},
        ).stdout.strip()

    def commit(self, subject: str, files: dict[str, str | None], body: str = "") -> str:
        for rel, text in files.items():
            path = self.root / rel
            if text is None:
                path.unlink()
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", subject, *(["-m", body] if body else []))
        return self.git("rev-parse", "--short", "HEAD")

    def check(
        self, base: str | None = None, head: str = "HEAD"
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--base", base or self.base, "--head", head],
            cwd=self.root,
            capture_output=True,
            text=True,
            env={**os.environ, **GIT_ENV},
            timeout=60,
            check=False,
        )


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    return Repo(tmp_path)


# ------------------------------------------------------------------ fails (negative first)
def test_code_and_tests_in_one_commit_without_red_line_fails(repo: Repo) -> None:
    sha = repo.commit(
        "feat: rule", {"backend/src/racket/rule.py": "r\n", "backend/tests/unit/test_r.py": "t\n"}
    )
    out = repo.check()
    assert out.returncode == 1, out.stdout + out.stderr
    assert "red-first: FAIL" in out.stdout
    line = next(x for x in out.stdout.splitlines() if sha in x)
    assert "feat: rule" in line
    assert "backend/src/racket/rule.py" in line
    assert "backend/tests" not in line


def test_web_code_before_its_tests_fails(repo: Repo) -> None:
    sha = repo.commit("feat: screen", {"web/src/app/s.tsx": "s\n"})
    repo.commit("test: screen", {"web/tests/unit/s.test.tsx": "t\n"})
    out = repo.check()
    assert out.returncode == 1, out.stdout
    assert sha in out.stdout


def test_red_in_subject_or_empty_red_line_is_not_a_red_step(repo: Repo) -> None:
    repo.commit("Red: in the subject", {"backend/src/racket/a.py": "a\n"})
    repo.commit("feat: b", {"backend/src/racket/b.py": "b\n"}, body="Red:")
    out = repo.check()
    assert out.returncode == 1
    assert "2 code commit(s) without a red step" in out.stdout


def test_unknown_ref_fails_closed(repo: Repo) -> None:
    out = repo.check(base="no-such-ref")
    assert out.returncode == 2
    assert "failing closed" in out.stdout


# ------------------------------------------------------------------ passes
def test_test_only_commit_before_code_passes(repo: Repo) -> None:
    repo.commit(
        "test: red", {"backend/tests/unit/test_r.py": "t\n", "tests/features/r.feature": "f"}
    )
    repo.commit("feat: rule", {"backend/src/racket/rule.py": "r\n"})
    repo.commit("refactor: rule", {"backend/src/racket/rule.py": "r2\n"})
    out = repo.check()
    assert out.returncode == 0, out.stdout
    assert "red-first: ok, 3 commit(s) checked" in out.stdout


def test_red_body_line_passes(repo: Repo) -> None:
    repo.commit(
        "feat: rule",
        {"backend/src/racket/rule.py": "r\n", "backend/tests/unit/test_r.py": "t\n"},
        body="Why.\n\nRed: uv run pytest tests/unit/test_r.py -> 1 failed",
    )
    assert repo.check().returncode == 0


def test_docs_only_and_empty_prs_pass(repo: Repo) -> None:
    assert repo.check(head=repo.base).returncode == 0
    repo.commit("docs: notes", {"docs/notes.md": "n\n"})
    out = repo.check()
    assert out.returncode == 0, out.stdout


def test_deleting_production_code_alone_is_not_a_code_commit(repo: Repo) -> None:
    repo.commit("chore: drop dead code", {"backend/src/racket/app.py": None})
    assert repo.check().returncode == 0


def test_merge_commits_and_mains_commits_are_not_judged(repo: Repo) -> None:
    repo.git("checkout", "-q", "main")
    repo.commit("feat: on main", {"backend/src/racket/main_only.py": "m\n"})
    new_main = repo.git("rev-parse", "HEAD")
    repo.git("checkout", "-q", "pr")
    repo.commit("test: red", {"backend/tests/unit/test_r.py": "t\n"})
    repo.git("merge", "-q", "--no-ff", "--no-edit", "main")  # main merged into the PR branch
    repo.commit("feat: rule", {"backend/src/racket/rule.py": "r\n"})
    out = repo.check(base=new_main)
    assert out.returncode == 0, out.stdout
    assert "2 commit(s) checked" in out.stdout
    assert "main_only" not in out.stdout
