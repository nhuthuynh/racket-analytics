#!/usr/bin/env python3
"""PreToolUse hook (ST-003, DPA/AI-10).

* Denies Write/Edit/MultiEdit/NotebookEdit to secret paths: `.env*`, `*.pem`, `*.key`,
  `infra/secrets/**` (exit 2, reason on stderr).
* Denies Bash commands that obviously write to those paths (redirection, tee, cp, mv, install).
* Appends every Bash command to `.claude/logs/bash-audit.jsonl` (gitignored).

Defensive by design: stdlib only, no network, and any internal error or malformed input
allows the call (exit 0) with a warning, so a hook bug can never wedge an agent session.
Reading secrets is governed by `permissions.deny` in settings.json, not here.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SECRET_DIRS = (PurePosixPath("infra/secrets"),)
BASH_WRITE_CMDS = {"cp", "mv", "install", "tee"}
REDIRECT_RE = re.compile(r"(?:^|[^<0-9&])(?:[0-9]?>>?|&>>?)\s*([^\s;&|<>]+)")


def project_dir(event: dict) -> Path:
    raw = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()
    return Path(raw).resolve()


def secret_reason(path_str: str, root: Path, cwd: Path) -> str | None:
    """Return why `path_str` is a secret path, or None."""
    if not path_str:
        return None
    candidate = Path(os.path.expanduser(path_str))
    if not candidate.is_absolute():
        candidate = cwd / candidate
    # Resolve `..` and symlinks (strict=False: the file may not exist yet).
    resolved = candidate.resolve()
    for p in {Path(os.path.normpath(candidate)), resolved}:
        name = p.name
        if name == ".env" or name.startswith(".env."):
            return f"{name} is an environment/secret file (.env*)"
        if name.endswith(".pem") or name.endswith(".key"):
            return f"{name} looks like a key or certificate (*.pem, *.key)"
        try:
            rel = PurePosixPath(p.relative_to(root).as_posix())
        except ValueError:
            continue
        for secret_dir in SECRET_DIRS:
            if rel == secret_dir or secret_dir in rel.parents:
                return f"{rel} is under {secret_dir}/"
    return None


def bash_targets(command: str) -> list[str]:
    """Best-effort list of paths a shell command writes to."""
    targets = [m.group(1) for m in REDIRECT_RE.finditer(command)]
    try:
        tokens = shlex.split(command, comments=True)
    except ValueError:
        tokens = command.split()
    segment: list[str] = []
    for tok in [*tokens, ";"]:
        if tok in {";", "&&", "||", "|", "&"}:
            if segment:
                cmd = os.path.basename(segment[0])
                args = [a for a in segment[1:] if not a.startswith("-")]
                if cmd == "tee":
                    targets.extend(args)
                elif cmd in BASH_WRITE_CMDS and args:
                    targets.append(args[-1])
            segment = []
        else:
            segment.append(tok)
    return targets


def audit(root: Path, command: str, decision: str) -> None:
    try:
        log_dir = root / ".claude" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "command": command,
            "decision": decision,
            "session_id": os.environ.get("CLAUDE_SESSION_ID", ""),
        }
        with (log_dir / "bash-audit.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError as exc:  # never block on a logging failure
        print(f"pre_tool_use: audit log not written: {exc}", file=sys.stderr)


def deny(reason: str) -> int:
    print(
        f"BLOCKED by .claude/hooks/pre_tool_use.py: {reason}. "
        "Secrets never go into the repo or agent edits (NFR-056); "
        "use infra/env.example for variable names and a secret store for values.",
        file=sys.stderr,
    )
    return 2


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
        if not isinstance(event, dict):
            raise ValueError("event is not an object")
    except (ValueError, OSError) as exc:
        print(f"pre_tool_use: ignoring malformed hook input ({exc})", file=sys.stderr)
        return 0

    root = project_dir(event)
    cwd = Path(event.get("cwd") or root)
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}

    if tool in WRITE_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        reason = secret_reason(str(path), root, cwd)
        return deny(f"write to {path!r} refused: {reason}") if reason else 0

    if tool == "Bash":
        command = str(tool_input.get("command", ""))
        for target in bash_targets(command):
            reason = secret_reason(target, root, cwd)
            if reason:
                audit(root, command, "deny")
                return deny(f"shell write to {target!r} refused: {reason}")
        audit(root, command, "allow")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a hook bug must not wedge the session
        print(f"pre_tool_use: internal error, allowing call: {exc!r}", file=sys.stderr)
        sys.exit(0)
