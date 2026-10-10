"""Binds tests/features/ci_e2e_stall_report.feature (CI-E2E-JOURNEYS-TIMEOUT; NFR-074): the
real Playwright of web/ (web/node_modules, installed by the infra-tests job) runs a stand-in
spec with the gated E2E step's reporters, read from ci.yml, and a short global timeout. No
browser is launched: the stand-in tests do not use a page."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO_ROOT
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("ci_e2e_stall_report.feature")

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
WEB = REPO_ROOT / "web"
PLAYWRIGHT = WEB / "node_modules" / ".bin" / "playwright"
GATED = '--grep-invert "@red-until-"'

SPEC = """import { test } from '@playwright/test';

test('first test passes', async () => {});

test('second test waits', async () => {
  test.setTimeout(0);
  await new Promise((resolve) => setTimeout(resolve, %d));
});
"""
CONFIG = """module.exports = { testDir: '.', workers: 1, retries: 0, timeout: 0 };
"""


def gated_reporters() -> str:
    """The ``--reporter`` value of the E2E job's gated Playwright step."""
    steps = yaml.safe_load(CI.read_text())["jobs"]["e2e"]["steps"]
    run = next(s["run"] for s in steps if GATED in s.get("run", ""))
    found = re.search(r"--reporter[= ](\S+)", run)
    assert found is not None, run
    return found.group(1)


@pytest.fixture
def playwright() -> Path:
    # Fails, never skips: the infra-tests job installs web/ (pnpm install --frozen-lockfile).
    assert PLAYWRIGHT.exists(), f"{PLAYWRIGHT} missing: run pnpm install --frozen-lockfile in web/"
    return PLAYWRIGHT


@given(
    parsers.parse(
        "the gated Playwright step's reporters from the CI workflow, "
        "with a global timeout of {seconds:d} seconds"
    ),
    target_fixture="options",
)
def options(seconds: int) -> list[str]:
    return [f"--reporter={gated_reporters()}", f"--global-timeout={seconds * 1000}"]


@when(
    parsers.parse(
        "Playwright runs a spec whose first test passes and whose second test waits "
        "for {seconds:d} seconds"
    ),
    target_fixture="result",
)
def run(tmp_path: Path, playwright: Path, options: list[str], seconds: int) -> dict[str, Any]:
    (tmp_path / "stall.spec.ts").write_text(SPEC % (seconds * 1000))
    (tmp_path / "playwright.config.cjs").write_text(CONFIG)
    report = tmp_path / "report"
    env = {
        **os.environ,
        "CI": "true",  # as on the runner: the HTML report is never opened or served
        "NODE_PATH": str(WEB / "node_modules"),  # '@playwright/test' from web/
        "PLAYWRIGHT_HTML_OUTPUT_DIR": str(report),
        "PLAYWRIGHT_HTML_OPEN": "never",
        "FORCE_COLOR": "0",
    }
    env.pop("GITHUB_ACTIONS", None)
    args = [str(playwright), "test", "-c", str(tmp_path / "playwright.config.cjs"), *options]
    started = time.monotonic()
    done = subprocess.run(
        args, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=180, check=False
    )
    return {
        "rc": done.returncode,
        "out": done.stdout + done.stderr,
        "elapsed": time.monotonic() - started,
        "report": report,
        "cmd": shlex.join(args),
    }


@then(parsers.parse("the run fails within {seconds:d} seconds"))
def fails_fast(result: dict[str, Any], seconds: int) -> None:
    assert result["rc"] != 0, result["out"]
    assert result["elapsed"] < seconds, (result["elapsed"], result["out"])


@then("the output names the second test as the one the timeout stopped")
def names_stopped(result: dict[str, Any]) -> None:
    out = result["out"]
    assert "Timed out waiting 5s for the test suite to run" in out, out
    assert re.search(r"\u2718\s+\d+ stall\.spec\.ts:\d+:\d+ \u203a second test waits", out), out


@then("the output prints the first test with its duration")
def prints_duration(result: dict[str, Any]) -> None:
    assert re.search(r"first test passes \(\d+(\.\d+)?m?s\)", result["out"]), result["out"]


@then("the HTML report is written")
def html_report(result: dict[str, Any]) -> None:
    index = result["report"] / "index.html"
    assert index.is_file(), (result["cmd"], result["out"])
