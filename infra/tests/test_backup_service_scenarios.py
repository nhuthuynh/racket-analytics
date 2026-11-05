"""Binds the process-level scenarios of tests/features/backup_service.feature (ST-076a;
NFR-045.1; ADR 0058 rules 1-3). ``scripts/ops/backup.py`` runs as a real process on a throwaway
backup directory; nothing reaches a database or a store, because each scenario ends before the
dump (status read, or a refusal). The Compose restore scenario is bound in
``test_backup_service_live.py`` (IT-05-03).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenario, then, when
from test_backup_service import IDENTITY, SCRIPT, plant_set

pytestmark = [pytest.mark.scenario, pytest.mark.unit]
FEATURE = "backup_service.feature"


@scenario(FEATURE, "A backup set taken 25 hours ago is stale")
def test_stale_set() -> None:
    pass


@scenario(FEATURE, "A backup set taken 23 hours ago is fresh")
def test_fresh_set() -> None:
    pass


@scenario(FEATURE, "With no encryption recipient nothing is written, but old sets are still pruned")
def test_no_recipient() -> None:
    pass


@scenario(FEATURE, "A private identity given as the recipient is refused")
def test_private_identity() -> None:
    pass


@pytest.fixture
def world(tmp_path: Path) -> dict[str, Any]:
    return {"dir": tmp_path, "env": {"BACKUP_DIR": str(tmp_path)}, "planted": {}}


def _run(world: dict[str, Any], *args: str) -> subprocess.CompletedProcess[str]:
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("BACKUP_", "PG", "S3_"))}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env={**clean, **world["env"]},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    world["proc"] = proc
    world["after"] = sorted(p.name for p in world["dir"].iterdir())
    return proc


@given(parsers.parse("a complete backup set taken {n:d} {unit} ago"))
def a_set(world: dict[str, Any], n: int, unit: str) -> None:
    age = timedelta(hours=n) if unit.startswith("hour") else timedelta(days=n)
    world["planted"][f"{n} {unit}"] = plant_set(world["dir"], datetime.now(UTC) - age)


@given("no encryption recipient is set")
def no_recipient(world: dict[str, Any]) -> None:
    world["env"].pop("BACKUP_AGE_RECIPIENT", None)


@given("the encryption recipient is an age private identity")
def private_identity(world: dict[str, Any]) -> None:
    world["env"]["BACKUP_AGE_RECIPIENT"] = IDENTITY


@when("the backup status is read")
def read_status(world: dict[str, Any]) -> None:
    _run(world, "--status")


@when("an on-demand backup runs")
def on_demand(world: dict[str, Any]) -> None:
    world["before"] = sorted(p.name for p in world["dir"].iterdir())
    _run(world, "--once")


@then(parsers.parse('the newest complete set is reported as "{state}"'))
def reported(world: dict[str, Any], state: str) -> None:
    report = json.loads(world["proc"].stdout)
    assert report["state"] == state, report
    assert report["taken_at"].endswith("Z")


@then(parsers.parse("the status command exits with code {rc:d}"))
@then(parsers.parse("the backup command exits with code {rc:d}"))
def exits(world: dict[str, Any], rc: int) -> None:
    proc = world["proc"]
    assert proc.returncode == rc, proc.stdout + proc.stderr


@then(parsers.parse('the backup command exits with code {rc:d} naming "{text}"'))
def exits_naming(world: dict[str, Any], rc: int, text: str) -> None:
    exits(world, rc)
    assert text in world["proc"].stdout + world["proc"].stderr


@then(parsers.parse("the set taken {n:d} {unit} ago is gone"))
def gone(world: dict[str, Any], n: int, unit: str) -> None:
    assert not world["planted"][f"{n} {unit}"].exists()


@then("no new backup set exists")
def no_new_set(world: dict[str, Any]) -> None:
    before = set(world.get("before", []))
    assert set(world["after"]) <= before, world["after"]
