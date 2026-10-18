"""Binds tests/features/e2e_projects.feature (FIX-04-1f; G04-07; api-sprint-04 §1 "Flag-on E2E").

The real Playwright of web/ (web/node_modules, installed by the infra-tests job) lists stand-in
specs through the real web/playwright.config.ts: a stand-in config imports it and only points
``testDir`` at a temporary tree laid out like web/e2e (``sprint-04/flags-on/`` for the flag-on
specs). ``--list`` launches no browser and needs no stack.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("e2e_projects.feature")

WEB = REPO_ROOT / "web"
PLAYWRIGHT = WEB / "node_modules" / ".bin" / "playwright"
CONFIG = """import base from {config!r};

export default {{ ...base, testDir: './e2e' }};
"""
SPEC = """import {{ test }} from '@playwright/test';

test({title!r}, async () => {{}});
"""
# `--list` prints one line per test and project, the parts joined by U+203A:
# "  [chromium] > sprint-04/x.spec.ts:3:5 > title" (">" standing for U+203A here).
SEP = "\u203a"
LISTED = re.compile(rf"^\s*\[(?P<project>[^\]]+)\] {SEP} .* {SEP} (?P<title>.+)$")


@dataclass
class Listing:
    rc: int
    out: str

    def projects_of(self, title: str) -> set[str]:
        found = (LISTED.match(line) for line in self.out.splitlines())
        return {m["project"] for m in found if m and m["title"].strip() == title}


@pytest.fixture
def playwright() -> Path:
    # Fails, never skips: the infra-tests job installs web/ (pnpm install --frozen-lockfile).
    assert PLAYWRIGHT.exists(), f"{PLAYWRIGHT} missing: run pnpm install --frozen-lockfile in web/"
    return PLAYWRIGHT


@pytest.fixture
def stand_in(tmp_path: Path) -> Path:
    root = tmp_path / "web-stand-in"
    (root / "e2e").mkdir(parents=True)
    config = str(WEB / "playwright.config.ts")
    (root / "playwright.config.ts").write_text(CONFIG.format(config=config))
    return root


@pytest.fixture
def ctx() -> dict[str, str]:
    return {}


def _spec(root: Path, relative: str, title: str) -> None:
    path = root / "e2e" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SPEC.format(title=title))


@given(parsers.parse('a flag-on spec "{flag_on}" and a spec "{plain}"'))
def specs(stand_in: Path, flag_on: str, plain: str) -> None:
    _spec(stand_in, "sprint-04/flags-on/age.spec.ts", flag_on)
    _spec(stand_in, "sprint-04/keyboard-and-narrow.spec.ts", plain)


@given(parsers.parse('the E2E projects are chosen with "{projects}"'))
def chosen(stand_in: Path, ctx: dict[str, str], projects: str) -> None:
    if not any((stand_in / "e2e").rglob("*.spec.ts")):
        _spec(stand_in, "sprint-01/sign-in.spec.ts", "E2E-01-02 sign in")
    ctx["PW_PROJECTS"] = projects


@when("the E2E specs are listed", target_fixture="listing")
def listed(playwright: Path, stand_in: Path, ctx: dict[str, str]) -> Listing:
    env = {
        **os.environ,
        "NODE_PATH": str(WEB / "node_modules"),  # '@playwright/test' of web/ for the stand-ins
        "FORCE_COLOR": "0",
        "PW_PROJECTS": ctx["PW_PROJECTS"],
    }
    for name in ("CI", "GITHUB_ACTIONS", "PW_CHROMIUM_CHANNEL", "BASE_URL"):
        env.pop(name, None)
    proc = subprocess.run(
        [str(playwright), "test", "--list", "-c", str(stand_in / "playwright.config.ts")],
        cwd=stand_in,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return Listing(proc.returncode, proc.stdout + proc.stderr)


@then(parsers.parse('the listing is refused naming "{known}"'))
def refused(listing: Listing, known: str) -> None:
    assert listing.rc != 0, listing.out
    assert "PW_PROJECTS" in listing.out, listing.out
    assert known in listing.out, listing.out


@then(parsers.re(r'"(?P<title>[^"]+)" is listed in "(?P<first>[^"]+)" and "(?P<second>[^"]+)"$'))
def listed_in_both(listing: Listing, title: str, first: str, second: str) -> None:
    assert listing.rc == 0, listing.out
    assert listing.projects_of(title) == {first, second}, listing.out


@then(parsers.re(r'"(?P<title>[^"]+)" is listed in "(?P<project>[^"]+)"$'))
def listed_in(listing: Listing, title: str, project: str) -> None:
    assert listing.rc == 0, listing.out
    assert listing.projects_of(title) == {project}, listing.out


@then(parsers.re(r'"(?P<title>[^"]+)" is not listed$'))
def not_listed(listing: Listing, title: str) -> None:
    assert listing.projects_of(title) == set(), listing.out
