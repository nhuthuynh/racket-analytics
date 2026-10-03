"""ST-003: scripts/test-unit.sh is the single unit-suite entry point (Stop hook, Makefile, CI)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit


def run_script(
    root: Path, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["RA_REPO_ROOT"] = str(root)
    env.update(extra_env or {})
    return subprocess.run(
        ["bash", str(SCRIPTS_DIR / "test-unit.sh")],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def fake_bin(tmp: Path, name: str, exit_code: int) -> Path:
    bindir = tmp / "bin"
    bindir.mkdir(exist_ok=True)
    tool = bindir / name
    tool.write_text(f'#!/bin/sh\necho "{name} $*" >> "{tmp}/calls.txt"\nexit {exit_code}\n')
    tool.chmod(0o755)
    return bindir


def test_failing_backend_unit_suite_fails_the_script(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "backend").mkdir(parents=True)
    (root / "backend" / "pyproject.toml").write_text("[project]\nname='x'\n")
    bindir = fake_bin(tmp_path, "uv", 1)
    res = run_script(root, {"PATH": f"{bindir}:{os.environ['PATH']}"})
    assert res.returncode != 0
    calls = (tmp_path / "calls.txt").read_text()
    assert "pytest" in calls
    assert "not slow" in calls
    assert "not red_until" in calls


def test_failing_web_unit_suite_fails_the_script(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "web" / "node_modules" / ".bin").mkdir(parents=True)
    (root / "web" / "package.json").write_text('{"scripts": {"test:unit": "vitest run"}}')
    bindir = fake_bin(tmp_path, "pnpm", 1)
    res = run_script(root, {"PATH": f"{bindir}:{os.environ['PATH']}"})
    assert res.returncode != 0
    assert "test:unit" in (tmp_path / "calls.txt").read_text()


def test_no_projects_yet_is_a_pass_with_a_note(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    res = run_script(root)
    assert res.returncode == 0
    assert "skipped" in res.stdout


def test_both_suites_green_passes(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "backend").mkdir(parents=True)
    (root / "backend" / "pyproject.toml").write_text("[project]\nname='x'\n")
    (root / "web" / "node_modules").mkdir(parents=True)
    (root / "web" / "package.json").write_text('{"scripts": {"test:unit": "vitest run"}}')
    fake_bin(tmp_path, "uv", 0)
    bindir = fake_bin(tmp_path, "pnpm", 0)
    res = run_script(root, {"PATH": f"{bindir}:{os.environ['PATH']}"})
    assert res.returncode == 0, res.stdout + res.stderr


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck not installed")
def test_script_passes_shellcheck() -> None:
    res = subprocess.run(
        ["shellcheck", str(SCRIPTS_DIR / "test-unit.sh")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stdout


def test_no_unit_tests_collected_is_not_a_failure(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "backend").mkdir(parents=True)
    (root / "backend" / "pyproject.toml").write_text("[project]\nname='x'\n")
    bindir = fake_bin(tmp_path, "uv", 5)  # pytest exit 5: no tests collected
    res = run_script(root, {"PATH": f"{bindir}:{os.environ['PATH']}"})
    assert res.returncode == 0, res.stdout
    assert "no unit tests collected" in res.stdout
