"""Steps for tests/features/gold_set_integrity.feature (ST-011, FR-151, NFR-078)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from racket.dataset.cli import main as manifest_check
from tests.support.paths import SYNTHETIC_60S

scenarios("gold_set_integrity.feature")


@pytest.fixture
def frozen_set(tmp_path: Path) -> Path:
    copy = tmp_path / "synthetic-60s"
    shutil.copytree(SYNTHETIC_60S, copy)
    return copy


@given("the synthetic fixture set version 1 is frozen")
def set_is_frozen(frozen_set: Path) -> None:
    manifest = json.loads((frozen_set / "manifest.json").read_text())
    assert manifest["version"] == 1
    assert manifest_check([str(frozen_set)]) == 0


@when("one of its files changes and the version stays the same", target_fixture="touched")
def change_a_file(frozen_set: Path) -> str:
    with (frozen_set / "clip.mp4").open("ab") as fh:
        fh.write(b"\x00")
    return "clip.mp4"


@when("a file that is not in its manifest is added to the set", target_fixture="touched")
def add_a_file(frozen_set: Path) -> str:
    (frozen_set / "better-clip.mp4").write_bytes(b"not in the manifest")
    return "better-clip.mp4"


@then("the integrity check fails and names the changed file")
@then("the integrity check fails and names the unlisted file")
def check_fails_naming(frozen_set: Path, touched: str, capsys: pytest.CaptureFixture[str]) -> None:
    capsys.readouterr()
    assert manifest_check([str(frozen_set)]) == 1
    failures = [line for line in capsys.readouterr().out.splitlines() if line.startswith("FAIL")]
    assert len(failures) == 1
    assert touched in failures[0]
