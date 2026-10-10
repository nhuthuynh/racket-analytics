"""Binds tests/features/footage_bucket_status.feature (FIX-03-1d, S3-DoD-P11): the measurement
script run as the reporter runs it, on recorded bucket probes written to a temporary directory."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR
from footage_bucket_fixtures import po_record, probe, sprint_plan
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("footage_bucket_status.feature")

SCRIPT = SCRIPTS_DIR / "measure" / "footage_bucket.py"


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    return {"dir": tmp_path, "po": po_record(), "probe": None}


@given("the PO record has no P11 answer")
def no_answer(ctx: dict) -> None:
    ctx["po"] = po_record()


@given(parsers.parse('the PO record answers P11 with "{decision}"'))
def po_answer(ctx: dict, decision: str) -> None:
    ctx["po"] = po_record(decision)


@given(parsers.re(r"the footage bucket (?P<state>exists|does not exist) and an anonymous read "
                  r"gets HTTP (?P<status>\d+)"))
def bucket(ctx: dict, state: str, status: str) -> None:
    ctx["probe"] = ctx["dir"] / "probe.json"
    ctx["probe"].write_text(probe(state == "exists", int(status)), encoding="utf-8")


@given(parsers.parse('a sprint plan whose S3-DoD-P11 row says "{status}"'))
def plan(ctx: dict, status: str) -> None:
    ctx["plan"] = ctx["dir"] / "sprint-03.md"
    ctx["plan"].write_text(sprint_plan(status), encoding="utf-8")


def _run(ctx: dict, *extra: str) -> None:
    po = ctx["dir"] / "po-input.md"
    po.write_text(ctx["po"], encoding="utf-8")
    cmd = [sys.executable, str(SCRIPT), "--po", str(po)]
    if ctx["probe"] is not None:
        cmd += ["--from-probe", str(ctx["probe"])]
    ctx["proc"] = subprocess.run([*cmd, *extra], capture_output=True, text=True, timeout=60)


@when("the footage bucket is measured")
def measure(ctx: dict) -> None:
    _run(ctx)


@when("the footage bucket is measured against the sprint plan")
def measure_against_plan(ctx: dict) -> None:
    _run(ctx, "--dod", str(ctx["plan"]))


@then("the measurement is refused as malformed")
def refused(ctx: dict) -> None:
    proc = ctx["proc"]
    assert proc.returncode == 2, proc.stdout + proc.stderr
    # The script's own refusal, not Python failing to find or run it.
    assert proc.stderr.startswith("footage_bucket: "), proc.stderr


@then(parsers.parse('the status is "{status}"'))
def status_is(ctx: dict, status: str) -> None:
    proc = ctx["proc"]
    assert proc.returncode in (0, 1), proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["status"] == status
    assert proc.returncode == (0 if status.startswith("met") else 1)


@then("the measurement reports that the sprint-DoD row disagrees")
def disagrees(ctx: dict) -> None:
    proc = ctx["proc"]
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "S3-DoD-P11" in proc.stderr
