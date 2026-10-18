"""Binds tests/features/check_flows.feature (PD-4b): docs/design/tools/check_flows.py run as a
process, as a reviewer runs it, on flows files written to a temporary directory and on the real
docs/design/flows-sprint-04.md (links resolved against the repository)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("check_flows.feature")

TOOL = REPO_ROOT / "docs" / "design" / "tools" / "check_flows.py"
FLOWS_04 = REPO_ROOT / "docs" / "design" / "flows-sprint-04.md"
ROLE = "security-privacy-engineer"
DECIDERS = ["senior-frontend-engineer", "pickleball-domain-coach", "product-manager", ROLE]
DECIDERS += ["business-analyst"]
SCREENS = ["P-01", "P-02", "P-03", "A-10", "A-11", "A-12", "A-13", "R-01", "Q-10"]


def _table(*cells: str) -> str:
    rows = "".join(f"| {ROLE} | R4-4 | 2026-10-17 | 2026-10-18 | {c} |\n" for c in cells)
    return (
        "## 14. Design review record (DR-04)\n\n| Role | Items | Opened | Due | Cell |\n"
        f"|---|---|---|---|---|\n{rows}\n## 15. Next\n"
    )


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    return {"file": tmp_path / "flows.md"}


@given(parsers.parse('a flows file whose security-privacy-engineer cell says "{cell}"'))
def one_row(ctx: dict, cell: str) -> None:
    ctx["file"].write_text(_table(cell), encoding="utf-8")


@given(parsers.parse('a flows file with the security-privacy-engineer cells "{a}" and "{b}"'))
def two_rows(ctx: dict, a: str, b: str) -> None:
    ctx["file"].write_text(_table(a, b), encoding="utf-8")


@given(parsers.parse('a flows file with a link to "{target}"'))
def with_link(ctx: dict, target: str) -> None:
    ctx["file"].write_text(f"[see]({target})\n| P-01 | Empty | card |\n", encoding="utf-8")


@given(parsers.parse('a flows file with the state row "{row}"'))
def with_state_row(ctx: dict, row: str) -> None:
    ctx["file"].write_text(f"{row} card |\n", encoding="utf-8")


@given("the Sprint 4 flows file")
def sprint_4(ctx: dict) -> None:
    ctx["file"] = FLOWS_04


@given("a flows file path that does not exist")
def missing(ctx: dict) -> None:
    ctx["file"] = ctx["file"].with_name("absent.md")


def _run(ctx: dict, *args: str) -> None:
    cmd = [sys.executable, "-I", str(TOOL), str(ctx["file"]), "--review", "DR-04", *args]
    ctx["result"] = subprocess.run(cmd, capture_output=True, text=True, check=False)


@when(parsers.parse("the checker runs with the decider {role}"))
def run_decider(ctx: dict, role: str) -> None:
    _run(ctx, "--decider", role)


@when(parsers.parse('the checker runs with the screen {screen} and the states "{states}"'))
def run_states(ctx: dict, screen: str, states: str) -> None:
    _run(ctx, "--screen", screen, "--states", states)


@when("the checker runs the opened form for DR-04 and its nine screens")
def run_opened(ctx: dict) -> None:
    args = ["--decider", "principal-designer"]
    args += [x for r in DECIDERS for x in ("--opened", r)]
    _run(ctx, *args, *[x for s in SCREENS for x in ("--screen", s)])


@then(parsers.parse('the checker exits {code:d} with "{text}"'))
def exits(ctx: dict, code: int, text: str) -> None:
    res = ctx["result"]
    assert (res.returncode, text in res.stdout) == (code, True), res.stdout + res.stderr
