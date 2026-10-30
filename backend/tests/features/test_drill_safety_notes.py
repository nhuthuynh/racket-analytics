"""CLI binding of tests/features/drill_safety_notes.feature (QA-VERIFY04R3-09; FR-140, FR-141;
QD-DR-04): ``racket-drill-lint`` over one drill file written from a reviewed library drill, and
over ``content/drills``. Written red first."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.integration.test_it_03_14_drill_lint import LIBRARY, LINT

scenarios("drill_safety_notes.feature")

BASE = LIBRARY / "pb.warm-up.shadow-footwork" / "v1.json"


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(parsers.parse('a {status} drill tagged "{skill}" with an empty safety note'))
def movement_drill(ctx: dict[str, Any], tmp_path: Path, status: str, skill: str) -> None:
    doc = json.loads(BASE.read_text(encoding="utf-8"))
    doc.update(
        id="pb.test.safety-drill",
        skills=[s for s in doc["skills"] if s != "footwork"] + [skill],
        review_status=status,
        safety_notes="",
        progressions=[],
        regressions=[],
    )
    path = tmp_path / "v1.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    ctx["path"], ctx["drill"] = path, doc["id"]


@given("the starter drill library")
def starter_library(ctx: dict[str, Any]) -> None:
    ctx["path"] = LIBRARY


@when("the drill is linted")
def linted(ctx: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    capsys.readouterr()
    ctx["rc"] = int(LINT.load()([str(ctx["path"])]))
    out, err = capsys.readouterr()
    ctx["out"] = out + err


@then(parsers.parse('the lint fails naming the drill and "{reason}"'))
def fails_naming(ctx: dict[str, Any], reason: str) -> None:
    assert ctx["rc"] == 1, ctx["out"]
    assert f"drill {ctx['drill']}: {reason}" in ctx["out"], ctx["out"]


@then("the lint passes")
def passes(ctx: dict[str, Any]) -> None:
    assert ctx["rc"] == 0, ctx["out"]


@then(parsers.parse("the current version of {drill} has a safety note"))
def current_has_note(drill: str) -> None:
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in (LIBRARY / drill).glob("v*.json")]
    current = [d for d in docs if "deprecated_by" not in d]
    assert len(current) == 1, [d["version"] for d in current]
    assert current[0]["review_status"] in ("coach-reviewed", "verified")
    assert current[0]["safety_notes"].strip(), current[0]
