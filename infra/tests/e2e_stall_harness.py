"""Harness for tests/features/ci_e2e_stall_report.feature (CI-STALL-SCENARIO-RACE).

Runs the real Playwright of web/ on a stand-in spec whose second test writes a start marker
(``<epoch ms> <worker pid>``) and then waits. The global timeout is set from the measured start-up
of that second test, so "the second test has started" holds before the timeout bites instead of
racing worker start-up on a loaded runner.
"""

from __future__ import annotations

import math
import os
import re
import shlex
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

MIN_GLOBAL_TIMEOUT_S = 5
START_UP_FACTOR = 3
# A runner that needs longer than this to start one test cannot run the scenario meaningfully.
MAX_GLOBAL_TIMEOUT_S = 60
MARKER_WAIT_S = 120.0

GATED = '--grep-invert "@red-until-"'

SPEC = """import { test } from '@playwright/test';
import { writeFileSync } from 'node:fs';

test('first test passes', async () => {});

test('second test waits', async () => {
  writeFileSync(process.env.STALL_MARKER!, `${Date.now()} ${process.pid}`);
  test.setTimeout(0);
  await new Promise((resolve) => setTimeout(resolve, %d));
});
"""
CONFIG = """module.exports = { testDir: '.', workers: 1, retries: 0, timeout: 0 };
"""


def global_timeout_s(start_up_s: float) -> int:
    """Whole seconds: at least 5, and three times the measured start-up of the second test."""
    if not math.isfinite(start_up_s) or start_up_s < 0:
        raise ValueError(f"start-up must be a finite, non-negative number of seconds: {start_up_s}")
    return max(MIN_GLOBAL_TIMEOUT_S, math.ceil(START_UP_FACTOR * start_up_s))


def gated_reporters(ci_yml: Path) -> str:
    """The ``--reporter`` value of the E2E job's gated Playwright step."""
    steps = yaml.safe_load(ci_yml.read_text())["jobs"]["e2e"]["steps"]
    run = next(s["run"] for s in steps if GATED in s.get("run", ""))
    found = re.search(r"--reporter[= ](\S+)", run)
    assert found is not None, run
    return found.group(1)


def resolve_reporters(value: str, web: Path) -> str:
    """Playwright resolves a reporter path against the config's directory, which is web/ in CI.
    The stand-in config lives elsewhere, so relative paths are made absolute against web/."""
    return ",".join(
        str((web / item).resolve()) if item.startswith(("./", "../")) else item
        for item in value.split(",")
    )


def read_marker(marker: Path) -> tuple[float, int] | None:
    """(epoch seconds, worker pid) written by the second test, or None before it has started."""
    try:
        text = marker.read_text().split()
    except FileNotFoundError:
        return None
    if len(text) != 2:  # written but not yet complete
        return None
    return int(text[0]) / 1000, int(text[1])


@dataclass
class Run:
    rc: int
    out: str
    elapsed: float
    global_timeout: int
    second_started: float | None  # seconds after launch
    frozen: float | None  # seconds after launch the worker was frozen
    report: Path
    cmd: str


class StandIn:
    """One directory with the stand-in spec and config, and the environment to run it in."""

    def __init__(self, root: Path, playwright: Path, web: Path, wait_s: int) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        (root / "stall.spec.ts").write_text(SPEC % (wait_s * 1000))
        (root / "playwright.config.cjs").write_text(CONFIG)
        self.playwright = playwright
        self.web = web
        self.marker = root / "second-test-started"
        self.report = root / "report"

    def _env(self) -> dict[str, str]:
        env = {
            **os.environ,
            "CI": "true",  # as on the runner: the HTML report is never opened or served
            "NODE_PATH": str(self.web / "node_modules"),  # '@playwright/test' from web/
            "PLAYWRIGHT_HTML_OUTPUT_DIR": str(self.report),
            "PLAYWRIGHT_HTML_OPEN": "never",
            "FORCE_COLOR": "0",
            "STALL_MARKER": str(self.marker),
        }
        env.pop("GITHUB_ACTIONS", None)
        return env

    def _start(self, options: list[str], log: Path) -> tuple[subprocess.Popen[bytes], float, str]:
        self.marker.unlink(missing_ok=True)
        args = [str(self.playwright), "test", "-c", str(self.root / "playwright.config.cjs")]
        args += options
        with log.open("wb") as sink:
            launched = time.time()
            proc = subprocess.Popen(  # noqa: S603  (fixed argv, no shell)
                args,
                cwd=self.root,
                env=self._env(),
                stdout=sink,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # its own group: the worker is cleaned up with it
            )
        return proc, launched, shlex.join(args)

    def _wait_for_marker(self, proc: subprocess.Popen[bytes]) -> tuple[float, int] | None:
        deadline = time.monotonic() + MARKER_WAIT_S
        while time.monotonic() < deadline:
            found = read_marker(self.marker)
            if found is not None or proc.poll() is not None:
                return found
            time.sleep(0.02)
        return None

    @staticmethod
    def _kill(proc: subprocess.Popen[bytes], worker: int | None) -> None:
        for pid in filter(None, [worker]):
            for sig in (signal.SIGCONT, signal.SIGKILL):
                try:
                    os.kill(pid, sig)
                except ProcessLookupError:
                    pass
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=30)

    def measure_start_up(self, reporters: str) -> float:
        """Seconds from launching Playwright until the second test has started, without a
        global timeout; the warm-up run is stopped as soon as the second test starts."""
        proc, launched, cmd = self._start([f"--reporter={reporters}"], self.root / "warm-up.log")
        found = None
        try:
            found = self._wait_for_marker(proc)
        finally:
            self._kill(proc, found[1] if found else None)
        log = (self.root / "warm-up.log").read_text(errors="replace")
        assert found is not None, f"the second test never started: {cmd}\n{log}"
        return max(0.0, found[0] - launched)

    def run(self, reporters: str, global_timeout: int, *, freeze_worker: bool) -> Run:
        """Run with the global timeout. With ``freeze_worker``, the worker is stopped (SIGSTOP)
        as soon as the second test has started and stays stopped until Playwright has exited,
        so it cannot answer the runner's stop: the worst case of a loaded runner."""
        options = [f"--reporter={reporters}", f"--global-timeout={global_timeout * 1000}"]
        log = self.root / "run.log"
        proc, launched, cmd = self._start(options, log)
        found = None
        frozen = None
        try:
            if freeze_worker:
                found = self._wait_for_marker(proc)
                if found is not None:
                    os.kill(found[1], signal.SIGSTOP)
                    frozen = time.time() - launched
            rc = proc.wait(timeout=180)
            elapsed = time.time() - launched
            found = found or read_marker(self.marker)
        finally:
            self._kill(proc, found[1] if found else None)
        return Run(
            rc=rc,
            out=log.read_text(errors="replace"),
            elapsed=elapsed,
            global_timeout=global_timeout,
            second_started=(found[0] - launched) if found else None,
            frozen=frozen,
            report=self.report,
            cmd=cmd,
        )
