#!/usr/bin/env python3
"""Run a command under a wall-clock budget (NFR-073: domain unit suite < 10 s, backend unit
suite <= 60 s, integration + scenario < 10 min).

Usage: run_with_budget.py SECONDS -- command [args...]
Exit: the command's exit code; 124 when the budget is exceeded (the command is killed).
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time


def main(argv: list[str]) -> int:
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
        return 124
    elapsed = time.monotonic() - start
    if code == 0:
        print(f"budget: finished in {elapsed:.1f}s, within budget of {budget:g}s")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
