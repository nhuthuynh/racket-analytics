#!/usr/bin/env python3
"""Run a command under a wall-clock budget (NFR-073: domain unit suite < 10 s, backend unit
suite <= 60 s, integration + scenario < 10 min).

Usage: run_with_budget.py SECONDS [--json PATH] -- command [args...]
Exit: the command's exit code; 124 when the budget is exceeded (the command is killed).
With --json, writes {"budget_s", "elapsed_s", "rc", "within_budget", "command"} to PATH, so
each CI run keeps the measured suite time as evidence (CI-PERF-GATES).
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def _record(path: Path | None, budget: float, elapsed: float, rc: int, within: bool,
            cmd: list[str]) -> None:  # fmt: skip
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "budget_s": budget,
        "elapsed_s": round(elapsed, 1),
        "rc": rc,
        "within_budget": within,
        "command": cmd,
    }
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    record: Path | None = None
    if len(argv) >= 3 and argv[1] == "--json":
        record, argv = Path(argv[2]), [argv[0], *argv[3:]]
    if len(argv) < 3 or argv[1] != "--":
        print(__doc__)
        return 2
    budget = float(argv[0])
    cmd = argv[2:]
    start = time.monotonic()
    proc = subprocess.Popen(cmd, start_new_session=True)
    try:
        code = proc.wait(timeout=budget)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        print(f"budget: '{' '.join(cmd)}' exceeded its time budget of {budget:g}s and was stopped")
        _record(record, budget, time.monotonic() - start, 124, False, cmd)
        return 124
    elapsed = time.monotonic() - start
    _record(record, budget, elapsed, code, True, cmd)
    if code == 0:
        print(f"budget: finished in {elapsed:.1f}s, within budget of {budget:g}s")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
