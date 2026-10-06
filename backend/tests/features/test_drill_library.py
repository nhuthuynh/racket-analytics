"""CLI binding of tests/features/drill_library.feature (QA-ACC-3 for ST-053; FR-140). Each
Examples row maps to the negative fixture named by its rule (IT-03-14's interface:
``backend/tests/fixtures/drills-invalid/<rule>.json``); the deprecated-drill scenario reads the
fixture library ``content/drills``. Written red first: ``red_until`` ST-053.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.integration.test_it_03_14_drill_lint import INVALID, LIBRARY, LINT, _drills

pytestmark = [pytest.mark.red_until(story="ST-053")]

scenarios("drill_library.feature")

BREAKS = {
    'targets metric "AN-99"': "unknown-metric",
    "lists itself as its own progression": "progression-cycle",
    "lasts 46 minutes": "duration-over-45",
    "has a success criterion with no number": "criterion-no-number",
    "has neither a source nor a rationale": "no-source",
}


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(parsers.parse("a drill file that {breaks}"))
def drill_file(ctx: dict[str, Any], breaks: str) -> None:
    ctx["path"] = INVALID / f"{BREAKS[breaks]}.json"
    assert ctx["path"].exists(), f"missing fixture {ctx['path'].name}"
    ctx["drill"] = json.loads(ctx["path"].read_text())["id"]


@given("a drill at version 2 that was later deprecated")
def deprecated_v2(ctx: dict[str, Any]) -> None:
    found = [
        p
        for p in _drills(LIBRARY)
        if (doc := json.loads(p.read_text())).get("version") in (2, "2")
        and "deprecated" in json.dumps(doc).lower()
    ]
    assert found, "the fixture library has no deprecated version-2 drill"
    ctx["path"], ctx["drill_doc"] = LIBRARY, json.loads(found[0].read_text())
    ctx["file"] = found[0]


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


@then("version 2 is still present with its content")
def still_present(ctx: dict[str, Any]) -> None:
    assert ctx["rc"] == 0, ctx["out"]
    assert json.loads(ctx["file"].read_text()) == ctx["drill_doc"]
    assert ctx["drill_doc"].get("setup") or ctx["drill_doc"].get("description"), "no content"
