"""Binds tests/features/check_threat_notes.feature (SEC-5): check_threat_notes.py
(docs/security/tools/) run as a process, as a reviewer runs it, on planted notes files and
on the real docs/security/threat-notes-sprint-05.md, with ADR ids resolved against the real
docs/decisions."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("check_threat_notes.feature")

TOOL = REPO_ROOT / "docs" / "security" / "tools" / "check_threat_notes.py"
NOTES_05 = REPO_ROOT / "docs" / "security" / "threat-notes-sprint-05.md"
TOPICS_05 = ["NFR-069.1", "NFR-045.1", "USAB-1.1", "REL-1.2", "NFR-050.9"]


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    return {"file": tmp_path / "notes.md", "args": []}


@given(parsers.parse('a threat-notes file with the row "{row}"'))
def planted(ctx: dict, row: str) -> None:
    head = "| ID | STRIDE | Threat | Control | Source | Story | Test | Status |\n"
    head += "|---|---|---|---|---|---|---|---|\n"
    ctx["file"].write_text(head + row + "\n", encoding="utf-8")


@given("the Sprint 5 threat notes")
def sprint_5(ctx: dict) -> None:
    ctx["file"] = NOTES_05


def _run(ctx: dict, *args: str) -> None:
    cmd = [sys.executable, "-I", str(TOOL), str(ctx["file"]), *args]
    ctx["result"] = subprocess.run(cmd, capture_output=True, text=True, check=False)


@when("the threat-notes checker runs on it")
def run_plain(ctx: dict) -> None:
    _run(ctx)


@when("the threat-notes checker runs with the Sprint 5 topics and the disclaimer")
def run_topics(ctx: dict) -> None:
    _run(ctx, *[x for t in TOPICS_05 for x in ("--topic", t)], "--disclaimer")


@then(parsers.parse('the threat-notes checker exits {code:d} with "{text}"'))
def exits(ctx: dict, code: int, text: str) -> None:
    res = ctx["result"]
    assert (res.returncode, text in res.stdout) == (code, True), res.stdout + res.stderr
