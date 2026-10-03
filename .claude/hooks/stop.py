#!/usr/bin/env python3
"""Stop hook (ST-003, DPA/AI-10): the unit suite must pass before a turn may end.

* Runs `scripts/test-unit.sh` (override: RA_UNIT_TEST_CMD, a shell command).
* Exit 2 with the failing output tail on stderr: Claude keeps working to fix it.
* `stop_hook_active` true means Claude is already continuing because of this hook; we
  allow the stop to avoid an endless loop (the failure was already reported once).
* A fingerprint of the working tree (HEAD + diff + untracked files) is cached after a
  green run, so turns that changed nothing do not re-run the suite.
* Over the time budget (RA_STOP_TIMEOUT_S, default 180 s; NFR-073 says <= 60 s) blocks.
* Inside GitHub Actions (the claude-code-action review bot) the CI jobs are the gate, so
  the hook does nothing.
* Malformed input or an internal error allows the stop with a warning.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

STATE_FILE = Path(".claude") / "logs" / "stop-last-green"
IGNORED_PREFIXES = (".claude/logs/",)
TAIL_LINES = 60


def git(root: Path, *args: str) -> bytes | None:
    try:
        res = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return res.stdout if res.returncode == 0 else None


def fingerprint(root: Path) -> str | None:
    """Hash of everything that could change test results; None outside git."""
    if git(root, "rev-parse", "--is-inside-work-tree") is None:
        return None
    h = hashlib.sha256()
    h.update(git(root, "rev-parse", "HEAD") or b"no-head")
    h.update(git(root, "diff", "HEAD", "--binary", "--", ".", ":!.claude/logs") or b"")
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z") or b""
    for name in sorted(n for n in untracked.split(b"\0") if n):
        rel = name.decode(errors="replace")
        if rel.startswith(IGNORED_PREFIXES):
            continue
        h.update(name)
        try:
            h.update(hashlib.sha256((root / rel).read_bytes()).digest())
        except OSError:
            h.update(b"unreadable")
    return h.hexdigest()


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
        if not isinstance(event, dict):
            raise ValueError("event is not an object")
    except (ValueError, OSError) as exc:
        print(f"stop: ignoring malformed hook input ({exc})", file=sys.stderr)
        return 0
    if event.get("stop_hook_active"):
        return 0
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # CI review bot (claude-code-action): the CI unit job is the gate there.
        return 0

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()).resolve()
    cmd = os.environ.get("RA_UNIT_TEST_CMD")
    if not cmd:
        script = root / "scripts" / "test-unit.sh"
        if not script.is_file():
            print("stop: scripts/test-unit.sh missing; unit gate skipped", file=sys.stderr)
            return 0
        cmd = f'bash "{script}"'

    state = root / STATE_FILE
    tree = fingerprint(root)
    fp = hashlib.sha256(f"{tree}\0{cmd}".encode()).hexdigest() if tree is not None else None
    if fp is not None and state.is_file() and state.read_text().strip() == fp:
        return 0
    budget = float(os.environ.get("RA_STOP_TIMEOUT_S", "180"))
    proc = subprocess.Popen(  # noqa: S602 - command is repo-controlled config, not user input
        cmd,
        shell=True,
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        out, _ = proc.communicate(timeout=budget)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(OSError):
            os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        print(
            f"stop: unit suite exceeded its time budget of {budget:.0f}s. Unit tests must be "
            "fast and isolated (EP/ENG-17, NFR-073); find the slow test and fix it.",
            file=sys.stderr,
        )
        return 2

    if proc.returncode != 0:
        tail = "\n".join((out or "").splitlines()[-TAIL_LINES:])
        print(
            "stop: the unit suite is failing, so this turn cannot end yet. Fix the code, not "
            f"the test (EP/ENG-28). Command: {cmd}\n{tail}",
            file=sys.stderr,
        )
        return 2

    if fp is not None:
        try:
            state.parent.mkdir(parents=True, exist_ok=True)
            state.write_text(fp)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a hook bug must not wedge the session
        print(f"stop: internal error, allowing stop: {exc!r}", file=sys.stderr)
        sys.exit(0)
