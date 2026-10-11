"""Binds tests/features/repo_visibility_status.feature (FIX-03-1c, S3-DoD-P10): the measurement
script run as the reporter runs it, on recorded GitHub answers written to a temporary directory."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR
from pytest_bdd import given, parsers, scenarios, then, when
from repo_visibility_fixtures import PUBLIC, answer, po_record, sprint_plan

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("repo_visibility_status.feature")

SCRIPT = SCRIPTS_DIR / "measure" / "repo_visibility.py"


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    return {"dir": tmp_path, "po": po_record()}


def _answer(ctx: dict, status: int, body: str) -> None:
    ctx["answer"] = ctx["dir"] / "answer.json"
    ctx["answer"].write_text(answer(status, body), encoding="utf-8")


@given("GitHub answers with HTTP 200 and no visibility field")
def no_visibility(ctx: dict) -> None:
    _answer(ctx, 200, json.dumps({"full_name": "o/r"}))


@given(parsers.parse('GitHub answers with HTTP 403 "{message}"'))
def rate_limited(ctx: dict, message: str) -> None:
    _answer(ctx, 403, json.dumps({"message": message}))


@given("GitHub reports the repository as public")
def public(ctx: dict) -> None:
    _answer(ctx, 200, PUBLIC)


@given("GitHub answers an anonymous reader with HTTP 404")
def not_found(ctx: dict) -> None:
    _answer(ctx, 404, json.dumps({"message": "Not Found"}))


@given("the PO record has no P10 answer")
def no_answer(ctx: dict) -> None:
    ctx["po"] = po_record()


@given(parsers.parse('the PO record answers P10 with "{decision}"'))
def po_answer(ctx: dict, decision: str) -> None:
    ctx["po"] = po_record(decision)


@given(parsers.parse('a sprint plan whose S3-DoD-P10 row says "{status}"'))
def plan(ctx: dict, status: str) -> None:
    ctx["plan"] = ctx["dir"] / "sprint-03.md"
    ctx["plan"].write_text(sprint_plan(status), encoding="utf-8")


def _run(ctx: dict, *extra: str) -> None:
    po = ctx["dir"] / "po-input.md"
    po.write_text(ctx["po"], encoding="utf-8")
    cmd = [sys.executable, str(SCRIPT), "--from-answer", str(ctx["answer"]), "--po", str(po)]
    ctx["proc"] = subprocess.run([*cmd, *extra], capture_output=True, text=True, timeout=60)


@when("the visibility is measured")
def measure(ctx: dict) -> None:
    _run(ctx)


@when("the visibility is measured against the sprint plan")
def measure_against_plan(ctx: dict) -> None:
    _run(ctx, "--dod", str(ctx["plan"]))


@then("the measurement is refused as malformed")
def refused(ctx: dict) -> None:
    proc = ctx["proc"]
    assert proc.returncode == 2, proc.stdout + proc.stderr
    # The script's own refusal, not Python failing to find or run it.
    assert proc.stderr.startswith("repo_visibility: "), proc.stderr


@then(parsers.re(r"""the status is ['"](?P<status>.+)['"]$"""))
def status_is(ctx: dict, status: str) -> None:
    proc = ctx["proc"]
    assert proc.returncode in (0, 1), proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["status"] == status
    assert proc.returncode == (0 if status.startswith("met") else 1)


@then("the measurement reports that the sprint-DoD row disagrees")
def disagrees(ctx: dict) -> None:
    proc = ctx["proc"]
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "S3-DoD-P10" in proc.stderr
