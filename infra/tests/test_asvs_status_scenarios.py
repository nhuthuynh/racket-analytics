"""Binds tests/features/asvs_status.feature (ST-078a): asvs_status.py (docs/security/tools/)
run as a process, as the G05-07 method runs it, on planted checklists and on the real
docs/security/asvs-l2-checklist.md."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("asvs_status.feature")

TOOL = REPO_ROOT / "docs" / "security" / "tools" / "asvs_status.py"
CHECKLIST = REPO_ROOT / "docs" / "security" / "asvs-l2-checklist.md"
RULES = "not-assessed,fail-without-owner,pass-without-evidence"
HEAD = (
    "| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |\n"
    "|---|---|---|---|---|---|---|\n"
)
TITLES = {"V1": "Encoding and Sanitization", "V3": "Web Frontend Security", "V5": "File Handling"}


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    return {"file": tmp_path / "checklist.md", "rows": {}}


def _write(ctx: dict) -> None:
    body = "# ASVS checklist (planted)\n\n## Checklist\n\n"
    for chapter, rows in ctx["rows"].items():
        body += f"### {chapter} {TITLES[chapter]}\n\n{HEAD}" + "".join(r + "\n" for r in rows) + "\n"
    ctx["file"].write_text(body, encoding="utf-8")


@given(parsers.parse('an ASVS checklist with the {chapter} row "{row}"'))
def planted(ctx: dict, chapter: str, row: str) -> None:
    ctx["rows"].setdefault(chapter, []).append(row)
    _write(ctx)


@given(parsers.parse('the {chapter} row "{row}"'))
def planted_more(ctx: dict, chapter: str, row: str) -> None:
    planted(ctx, chapter, row)


@given("the real ASVS L2 checklist")
def real(ctx: dict) -> None:
    ctx["file"] = CHECKLIST


def _run(ctx: dict, *extra: str) -> None:
    cmd = [sys.executable, "-I", str(TOOL), str(ctx["file"]), "--level", "2", "--fail-on", RULES]
    ctx["result"] = subprocess.run([*cmd, *extra], capture_output=True, text=True, check=False)


@when("the ASVS status tool runs on it with the G05-07 rules")
def run_all(ctx: dict) -> None:
    _run(ctx)


@when(parsers.parse("the ASVS status tool runs on it with the G05-07 rules for chapters {spec}"))
def run_chapters(ctx: dict, spec: str) -> None:
    _run(ctx, "--chapters", spec)


@then(parsers.parse('the ASVS status tool exits {code:d} with "{text}"'))
def exits(ctx: dict, code: int, text: str) -> None:
    res = ctx["result"]
    assert (res.returncode, text in res.stdout) == (code, True), res.stdout + res.stderr
