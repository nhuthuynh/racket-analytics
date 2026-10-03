"""ST-003: PostToolUse formats and lints the edited file [DPA/AI-10, AQS/STACK-05].

Exit 2 after PostToolUse does not undo the edit; it feeds stderr back to Claude so the
remaining lint errors get fixed in the same turn.
"""

from __future__ import annotations

import shutil
import stat
import sys
from pathlib import Path

import pytest
from conftest import run_hook

pytestmark = pytest.mark.unit

HOOK = "post_tool_use.py"
RUFF = shutil.which("ruff") or str(Path(sys.executable).parent / "ruff")


def edit_call(path: Path, tool: str = "Edit") -> dict[str, object]:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": tool,
        "tool_input": {"file_path": str(path)},
        "tool_response": {"success": True},
    }


# ---------------------------------------------------------------- negative cases first
def test_unfixable_lint_error_is_reported_back(project: Path) -> None:
    src = project / "bad.py"
    src.write_text("def f():\n    return undefined_name\n")
    result = run_hook(HOOK, edit_call(src), project, {"RA_RUFF": RUFF})
    assert result.returncode == 2
    assert "F821" in result.stderr


def test_missing_ruff_does_not_block(project: Path) -> None:
    src = project / "a.py"
    src.write_text("x=1\n")
    result = run_hook(
        HOOK, edit_call(src), project, {"RA_RUFF": "/nonexistent/ruff", "PATH": "/usr/bin:/bin"}
    )
    assert result.returncode == 0
    assert "ruff not found" in result.stderr


def test_deleted_file_is_ignored(project: Path) -> None:
    result = run_hook(HOOK, edit_call(project / "gone.py"), project, {"RA_RUFF": RUFF})
    assert result.returncode == 0


def test_malformed_input_does_not_block(project: Path) -> None:
    result = run_hook(HOOK, "{not json", project)
    assert result.returncode == 0


# ---------------------------------------------------------------- positive cases
@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
def test_python_file_is_formatted_and_autofixed(project: Path, tool: str) -> None:
    src = project / "ugly.py"
    src.write_text("import os\nimport sys\nx=[1,2 ,3]\nprint(sys.argv,x)\n")
    result = run_hook(HOOK, edit_call(src, tool), project, {"RA_RUFF": RUFF})
    assert result.returncode == 0, result.stderr
    text = src.read_text()
    assert "x = [1, 2, 3]" in text
    assert "import os" not in text  # F401 auto-fixed


def test_non_code_file_is_untouched(project: Path) -> None:
    doc = project / "notes.md"
    doc.write_text("x=1\n")
    result = run_hook(HOOK, edit_call(doc), project, {"RA_RUFF": RUFF})
    assert result.returncode == 0
    assert doc.read_text() == "x=1\n"


def _fake_eslint(tmp: Path, exit_code: int) -> Path:
    log = tmp / "eslint-args.txt"
    script = tmp / "eslint"
    script.write_text(
        f'#!/bin/sh\necho "$@" > "{log}"\necho "eslint said no" >&2\nexit {exit_code}\n'
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_typescript_file_runs_eslint_fix(project: Path, tmp_path: Path) -> None:
    eslint = _fake_eslint(tmp_path, 0)
    src = project / "web" / "app" / "page.tsx"
    src.parent.mkdir(parents=True)
    src.write_text("export default function P(){return null}\n")
    result = run_hook(HOOK, edit_call(src), project, {"RA_ESLINT": str(eslint)})
    assert result.returncode == 0, result.stderr
    args = (tmp_path / "eslint-args.txt").read_text()
    assert "--fix" in args
    assert str(src) in args


def test_typescript_lint_failure_is_reported_back(project: Path, tmp_path: Path) -> None:
    eslint = _fake_eslint(tmp_path, 1)
    src = project / "web" / "lib" / "x.ts"
    src.parent.mkdir(parents=True)
    src.write_text("export const x = 1\n")
    result = run_hook(HOOK, edit_call(src), project, {"RA_ESLINT": str(eslint)})
    assert result.returncode == 2
    assert "eslint said no" in result.stderr


def test_typescript_without_eslint_installed_does_not_block(project: Path) -> None:
    src = project / "web" / "x.ts"
    src.parent.mkdir(parents=True)
    src.write_text("export const x = 1\n")
    result = run_hook(HOOK, edit_call(src), project)
    assert result.returncode == 0
    assert "eslint not installed" in result.stderr
