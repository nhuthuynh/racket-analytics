"""Binds tests/features/restore_drill.feature (ST-076c; NFR-045.1-.4; ADR 0058 rule 4; G05-03).

The ``@integration`` examples run the real ``scripts/ops/restore_drill.py`` on a Compose project
of their own (``--services api``: the API and what it needs, so the drill fits a test run; the
G05-03 measurement runs the whole stack). Each drill builds images and starts a stack, so
they run only with ``RESTORE_DRILL_LIVE=1`` (the infra CI job has a 10-minute budget; QA-PIN-05
pins the drill to its CI or nightly step). The ``@unit`` example checks a recorded report.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from conftest import REPO_ROOT
from pytest_bdd import given, parsers, scenario, then, when

SCRIPT = REPO_ROOT / "scripts" / "ops" / "restore_drill.py"
FIXTURES = Path(__file__).parent / "fixtures" / "restore_drill"
FEATURE = "restore_drill.feature"
live = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RESTORE_DRILL_LIVE") != "1" or shutil.which("docker") is None,
        reason="live restore drill: set RESTORE_DRILL_LIVE=1 (needs Docker)",
    ),
]


@pytest.mark.scenario
@live[0]
@live[1]
@scenario(FEATURE, "clean drill")
def test_clean_drill() -> None:
    pass


@pytest.mark.scenario
@live[0]
@live[1]
@scenario(FEATURE, "a correction lost")
def test_correction_lost() -> None:
    pass


@pytest.mark.scenario
@pytest.mark.unit
@scenario(FEATURE, "the recorded report of a planted drill fails the check")
def test_recorded_planted_report() -> None:
    pass


def drill(tmp_path: Path, *extra: str) -> dict[str, Any]:
    out = tmp_path / "restore-drill.json"
    project = f"racket-drill-it-{secrets.token_hex(3)}"
    args = ["--project", project, "--flags", "on", "--services", "api", "--json", str(out)]
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args, *extra],
        capture_output=True,
        text=True,
        timeout=3600,
        check=False,
        cwd=REPO_ROOT,
    )
    assert out.exists(), proc.stdout[-4000:] + proc.stderr[-4000:]
    return {"proc": proc, "report": json.loads(out.read_text())}


@pytest.fixture
def world() -> dict[str, Any]:
    return {}


@given("a seeded stack with a fresh backup")
def seeded(world: dict[str, Any]) -> None:
    world["extra"] = ()


@given("a backup taken after one confirmed correction was deleted")
def planted(world: dict[str, Any]) -> None:
    world["extra"] = ("--plant-delete-correction",)


@given("the recorded report of a drill with a planted deleted correction")
def recorded(world: dict[str, Any]) -> None:
    world["path"] = FIXTURES / "planted.json"


@when("the volumes are destroyed and restored")
@when("the drill compares fingerprints")
def run_drill(world: dict[str, Any], tmp_path: Path) -> None:
    world.update(drill(tmp_path, *world["extra"]))


@when("the report is checked")
def check_report(world: dict[str, Any]) -> None:
    world["proc"] = subprocess.run(
        [sys.executable, str(SCRIPT), "--check", str(world["path"])],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@then("the corrections count and SHA-256 equal the values before")
def corrections_equal(world: dict[str, Any]) -> None:
    assert "error" not in world["report"], world["report"]["error"]
    c = world["report"]["corrections"]
    assert c["equal"] is True, c
    assert c["before"] == c["after"]
    assert c["before"]["count"] >= 1, "a vacuous drill: no correction was seeded"


@then("the object count and SHA-256 equal the values before")
def objects_equal(world: dict[str, Any]) -> None:
    o = world["report"]["objects"]
    assert o["equal"] is True, o
    assert o["manifest_equal"] is True, o
    assert o["before"]["count"] >= 1, "a vacuous drill: no object was seeded"
    assert world["report"]["dangling_object_refs"] == []


@then("the RPO is at most 24 hours and the RTO at most 240 minutes")
def targets(world: dict[str, Any]) -> None:
    r = world["report"]
    assert 0 <= r["rpo_hours"] <= 24, r["rpo_hours"]
    assert 0 < r["rto_minutes"] <= 240, r["rto_minutes"]


@then(parsers.parse("the drill exits with code {rc:d}"))
def exits(world: dict[str, Any], rc: int) -> None:
    proc = world["proc"]
    assert proc.returncode == rc, proc.stdout[-4000:] + proc.stderr[-4000:]


@then(parsers.parse('the drill fails naming "{name}"'))
def fails_naming(world: dict[str, Any], name: str) -> None:
    proc = world["proc"]
    assert proc.returncode == 1, proc.stdout[-4000:] + proc.stderr[-4000:]
    assert name in proc.stderr
    if "report" in world:
        assert world["report"]["corrections"]["equal"] is False
        assert world["report"]["objects"]["equal"] is True, "only the planted row differs"
