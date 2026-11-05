"""Binds tests/features/browser_matrix.feature (ST-079; NFR-024.1-.3; G05-04).

web/'s real Playwright (web/node_modules, installed by the infra-tests job) runs a stand-in suite
laid out like web/e2e: the five E2E-04 journeys, sign-in and upload resume, tagged ``@critical``,
plus one untagged failing test that ``--grep @critical`` must leave out. The tests use no browser
fixture, so no browser is launched. The real ``scripts/measure/browser_matrix.py`` then reads the
JSON reports exactly as goal-scorecard §4 G05-04 does.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("browser_matrix.feature")

WEB = REPO_ROOT / "web"
PLAYWRIGHT = WEB / "node_modules" / ".bin" / "playwright"
MATRIX = SCRIPTS_DIR / "measure" / "browser_matrix.py"
PROJECTS = ("chromium", "webkit", "android-chrome")

NAMES = ", ".join(f"{{ name: '{p}' }}" for p in PROJECTS)
CONFIG = (
    "import { defineConfig } from '@playwright/test';\n"
    "export default defineConfig({ testDir: './e2e', retries: 0, workers: 1,\n"
    f"  projects: [{NAMES}] }});\n"
)

JOURNEYS = """import { expect, test } from '@playwright/test';
const flaky = process.env.STANDIN_FLAKY ?? '';
test.describe('Journeys', { tag: '@critical' }, () => {
  for (const id of ['E2E-04-01', 'E2E-04-02', 'E2E-04-03', 'E2E-04-04', 'E2E-04-05']) {
    test(`${id} journey`, async ({}, info) => {
      const planted = id === flaky && info.repeatEachIndex === 1; // fails its second repeat
      expect(planted).toBe(false);
    });
  }
});
test('not critical: always fails', async () => { expect(1).toBe(2); });
"""
SIGN_IN = """import { test } from '@playwright/test';
test.describe('Sign in without a memorised password', { tag: '@critical' }, () => {
  test('Sign up with an email sign-in link', async () => {});
  test('A link that can no longer be used: is 16 minutes old', async () => {
    test.skip(true, 'API level');
  });
});
"""
UPLOAD = """import { test } from '@playwright/test';
test.describe('Resumable upload', () => {
  test('Connection drops mid-upload (E2E-01-02)', { tag: '@critical' }, async () => {});
});
"""


@dataclass
class Run:
    suite: Path
    flaky: str = ""
    reports: dict[str, Path] = field(default_factory=dict)
    proc: subprocess.CompletedProcess[str] | None = None


def standin(tmp_path: Path, *, upload: bool = True) -> Path:
    suite = tmp_path / "suite"
    (suite / "e2e" / "sprint-04").mkdir(parents=True)
    (suite / "e2e" / "sprint-01").mkdir(parents=True)
    (suite / "playwright.config.ts").write_text(CONFIG)
    (suite / "e2e" / "sprint-04" / "journeys.spec.ts").write_text(JOURNEYS)
    (suite / "e2e" / "sprint-01" / "sign-in.spec.ts").write_text(SIGN_IN)
    if upload:
        (suite / "e2e" / "sprint-01" / "resumable-upload.spec.ts").write_text(UPLOAD)
    return suite


@pytest.fixture
def playwright() -> Path:
    assert PLAYWRIGHT.exists(), f"{PLAYWRIGHT} missing: run pnpm install --frozen-lockfile in web/"
    return PLAYWRIGHT


@given(
    parsers.re(r'the specs tagged "@critical" \(E2E-04-01..05, sign-in, upload resume\)'),
    target_fixture="run",
)
def all_critical(tmp_path: Path) -> Run:
    return Run(standin(tmp_path))


@given(
    parsers.parse('the specs tagged "@critical" with "{journey}" failing in its second repeat'),
    target_fixture="run",
)
def one_flaky(tmp_path: Path, journey: str) -> Run:
    return Run(standin(tmp_path), flaky=journey)


@given('the specs tagged "@critical" without the upload resume journey', target_fixture="run")
def no_upload(tmp_path: Path) -> Run:
    return Run(standin(tmp_path, upload=False))


@when(parsers.parse('they run in the "{project}" project 3 times with retries off'))
def run_project(run: Run, project: str, playwright: Path) -> None:
    report = run.suite / f"pw-{project}.json"
    env = {**os.environ, "NODE_PATH": str(WEB / "node_modules"), "STANDIN_FLAKY": run.flaky}
    env.pop("CI", None)
    with report.open("w") as out:
        subprocess.run(
            [
                str(playwright),
                "test",
                "-c",
                "playwright.config.ts",
                "--project",
                project,
                "--repeat-each",
                "3",
                "--grep",
                "@critical",
                "--reporter",
                "json",
            ],
            cwd=run.suite,
            env=env,
            stdout=out,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
            check=False,
        )
    run.reports[project] = report


def matrix(run: Run, *require: str) -> subprocess.CompletedProcess[str]:
    run.proc = subprocess.run(
        [
            sys.executable,
            str(MATRIX),
            *map(str, run.reports.values()),
            "--require",
            ",".join(require),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return run.proc


@then(parsers.parse('the browser-matrix method passes for "{project}"'))
def passes(run: Run, project: str) -> None:
    proc = matrix(run, project)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"{project}: ok" in proc.stdout


@then(parsers.parse('the browser-matrix method fails naming "{journey}" as flaky in "{project}"'))
def fails_flaky(run: Run, journey: str, project: str) -> None:
    proc = matrix(run, project)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert f"{project}: flaky {journey}" in proc.stdout


@then(parsers.parse('the browser-matrix method fails naming "{journey}" as missing in "{project}"'))
def fails_missing(run: Run, journey: str, project: str) -> None:
    proc = matrix(run, project)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert f"{project}: missing journey {journey}" in proc.stdout


@then(parsers.parse('the browser-matrix method fails when it also requires "{other}"'))
def fails_no_report(run: Run, other: str) -> None:
    proc = matrix(run, "chromium", other)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert f"{other}: no report" in proc.stdout
    assert "chromium: ok" in proc.stdout
