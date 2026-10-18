"""CLI binding of tests/features/drill_safety_notes.feature (FIX-04-1d; G04-05 (e); QD-DR-04)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.integration.test_drill_safety_notes import SAFETY, library_with, missing_safety_notes
from tests.integration.test_it_03_14_drill_lint import LIBRARY, LINT

scenarios("drill_safety_notes.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given("a coach-reviewed drill involving footwork with empty safety notes")
def reviewed_footwork(ctx: dict[str, Any]) -> None:
    ctx["path"] = SAFETY / "reviewed-footwork-no-notes.json"
    ctx["drill"] = "pb.safety.reviewed-footwork"


@given("a draft drill and a deprecated drill involving footwork with empty safety notes")
def draft_and_deprecated(ctx: dict[str, Any], tmp_path: Path) -> None:
    files = [SAFETY / "draft-footwork-no-notes.json", SAFETY / "deprecated-footwork-no-notes.json"]
    ctx["path"] = library_with(files, tmp_path / "drills")


@given("the drill library")
def the_library(ctx: dict[str, Any]) -> None:
    ctx["path"] = LIBRARY


@when("the library is validated")
def validated(ctx: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    capsys.readouterr()
    ctx["rc"] = int(LINT.load()([str(ctx["path"])]))
    out, err = capsys.readouterr()
    ctx["out"] = out + err


@then(parsers.parse('validation fails naming the drill and "{reason}"'))
def fails(ctx: dict[str, Any], reason: str) -> None:
    assert ctx["rc"] == 1, ctx["out"]
    assert ctx["drill"] in ctx["out"]
    assert reason in ctx["out"].lower()


@then("validation passes")
def passes(ctx: dict[str, Any]) -> None:
    assert ctx["rc"] == 0, ctx["out"]


@then("no current reviewed drill involving lobs, diving, sprints or footwork has empty safety notes")
def no_missing(ctx: dict[str, Any]) -> None:
    assert missing_safety_notes(ctx["path"]) == []
