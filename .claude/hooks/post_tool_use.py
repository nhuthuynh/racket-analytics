#!/usr/bin/env python3
"""PostToolUse hook (ST-003, DPA/AI-10, AQS/STACK-05).

After Edit/Write/MultiEdit on a code file:
* Python: `ruff check --fix`, then `ruff format`, then `ruff check` to report what is left.
* TypeScript/JavaScript: `eslint --fix <file>` from web/node_modules.

Exit 2 reports remaining lint errors to Claude (the edit itself is kept). Missing tools,
deleted files, malformed input or internal errors exit 0 with a note: the hook must never
block a session for reasons the agent cannot fix. CI runs the same linters as the gate.

Overrides (tests and unusual setups): RA_RUFF, RA_ESLINT point to the binaries.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

EDIT_TOOLS = {"Write", "Edit", "MultiEdit"}
PY_SUFFIXES = {".py", ".pyi"}
JS_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"}
TOOL_TIMEOUT_S = 30


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=TOOL_TIMEOUT_S, check=False
    )


def find_ruff(root: Path) -> str | None:
    override = os.environ.get("RA_RUFF")
    candidates = [override] if override else []
    candidates += [str(root / "backend" / ".venv" / "bin" / "ruff"), shutil.which("ruff")]
    for c in candidates:
        if c and Path(c).is_file() and os.access(c, os.X_OK):
            return c
    return None


def find_eslint(root: Path, file: Path) -> str | None:
    override = os.environ.get("RA_ESLINT")
    if override:
        return override if Path(override).is_file() else None
    for parent in file.parents:
        cand = parent / "node_modules" / ".bin" / "eslint"
        if cand.is_file():
            return str(cand)
        if parent == root:
            break
    return None


def nearest_config_dir(file: Path, root: Path, names: tuple[str, ...]) -> Path:
    for parent in file.parents:
        if any((parent / n).exists() for n in names):
            return parent
        if parent == root:
            break
    return root


def lint_python(file: Path, root: Path) -> int:
    ruff = find_ruff(root)
    if not ruff:
        print(
            "post_tool_use: ruff not found; skipped format/lint (CI still gates)", file=sys.stderr
        )
        return 0
    cwd = nearest_config_dir(file, root, ("pyproject.toml", "ruff.toml", ".ruff.toml"))
    run([ruff, "check", "--fix", "--quiet", str(file)], cwd)
    run([ruff, "format", "--quiet", str(file)], cwd)
    check = run([ruff, "check", "--quiet", "--output-format=concise", str(file)], cwd)
    if check.returncode != 0:
        print(
            f"post_tool_use: ruff found problems it could not fix in {file}:\n"
            f"{check.stdout}{check.stderr}",
            file=sys.stderr,
        )
        return 2
    return 0


def lint_js(file: Path, root: Path) -> int:
    eslint = find_eslint(root, file)
    if not eslint:
        print("post_tool_use: eslint not installed (web/node_modules); skipped", file=sys.stderr)
        return 0
    cwd = nearest_config_dir(file, root, ("package.json",))
    res = run([eslint, "--fix", str(file)], cwd)
    if res.returncode != 0:
        print(
            f"post_tool_use: eslint problems in {file}:\n{res.stdout}{res.stderr}", file=sys.stderr
        )
        return 2
    return 0


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
        if not isinstance(event, dict):
            raise ValueError("event is not an object")
    except (ValueError, OSError) as exc:
        print(f"post_tool_use: ignoring malformed hook input ({exc})", file=sys.stderr)
        return 0
    if event.get("tool_name") not in EDIT_TOOLS:
        return 0
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()).resolve()
    raw = (event.get("tool_input") or {}).get("file_path") or ""
    if not raw:
        return 0
    file = Path(raw)
    if not file.is_absolute():
        file = Path(event.get("cwd") or root) / file
    file = file.resolve()
    if not file.is_file():
        return 0
    if file.suffix in PY_SUFFIXES:
        return lint_python(file, root)
    if file.suffix in JS_SUFFIXES:
        return lint_js(file, root)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.TimeoutExpired as exc:
        print(f"post_tool_use: linter timed out ({exc.timeout}s); skipped", file=sys.stderr)
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001 - a hook bug must not wedge the session
        print(f"post_tool_use: internal error, skipped: {exc!r}", file=sys.stderr)
        sys.exit(0)
