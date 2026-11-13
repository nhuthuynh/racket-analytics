"""Binding of tests/features/golden_patterns.feature (QA-REF-GOLD; ADR 0061 Rule 6; NFR-078).

The frozen files listed in ``golden.lock.json`` are copied (repository-relative paths) into a
temporary folder, a scenario edits the copy, and ``integrity.check`` reads the copy with the
repository's ``docs/decisions/``. Written red first: before QA-REF-GOLD there is no lock.
"""

from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support.paths import REPO

scenarios("golden_patterns.feature")

GOLDEN = "backend/tests/regression/golden_patterns"
MEASURES = f"{GOLDEN}/vectors/measures.gs-pat-1-v1.json"
FIXTURE = "docs/domain/hand-counts/GS-PAT-1-v1.json"


def _integrity() -> ModuleType:
    try:
        return importlib.import_module("tests.regression.golden_patterns.integrity")
    except ImportError as exc:
        pytest.fail(f"RED until QA-REF-GOLD: no integrity check ({exc})", pytrace=False)


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path}


def _read_json(ctx: dict[str, Any], rel: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((ctx["root"] / rel).read_text(encoding="utf-8"))
    return data


def _write_json(ctx: dict[str, Any], rel: str, data: dict[str, Any]) -> None:
    (ctx["root"] / rel).write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


@given("the frozen golden pattern files and their lock")
def frozen(ctx: dict[str, Any]) -> None:
    lock_path = REPO / GOLDEN / "golden.lock.json"
    assert lock_path.is_file(), f"{GOLDEN}/golden.lock.json is missing"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    ctx["lock"] = lock
    for row in lock["changes"]:
        for rel in row["files"]:
            target = ctx["root"] / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((REPO / rel).read_bytes())


@given("the AN-09 value of gp1-doubles side A is edited in the measures vector")
def edit_vector(ctx: dict[str, Any]) -> None:
    data = _read_json(ctx, MEASURES)
    data["measures"]["gp1-doubles"]["A"]["AN-09"]["value"] = 0.75
    _write_json(ctx, MEASURES, data)


@given("a rally of gp2-singles is edited in the GS-PAT-1 fixture")
def edit_fixture(ctx: dict[str, Any]) -> None:
    data = _read_json(ctx, FIXTURE)
    data["matches"]["gp2-singles"]["labels"]["rallies"][0]["outcome"]["ending"] = "winner"
    _write_json(ctx, FIXTURE, data)


def _relock(ctx: dict[str, Any], adr: str) -> None:
    edit_vector(ctx)
    integrity = _integrity()
    row = copy.deepcopy(ctx["lock"]["changes"][-1])
    row.update(date="2026-12-01", adr=adr, reason="edited in a scenario")
    row["files"] = {MEASURES: integrity.sha256((ctx["root"] / MEASURES).read_bytes())}
    ctx["lock"] = {**ctx["lock"], "changes": [*ctx["lock"]["changes"], row]}


@given(parsers.parse('the measures vector is edited and locked by a row naming "{adr}"'))
def relock_named(ctx: dict[str, Any], adr: str) -> None:
    _relock(ctx, adr)


@given("the measures vector is edited and locked by a row naming the first row's ADR")
def relock_reused(ctx: dict[str, Any]) -> None:
    _relock(ctx, ctx["lock"]["changes"][0]["adr"])


@when("the golden integrity check runs")
def run(ctx: dict[str, Any]) -> None:
    integrity = _integrity()

    def read(rel: str) -> bytes | None:
        path = ctx["root"] / rel
        return path.read_bytes() if path.is_file() else None

    ctx["problems"] = integrity.check(ctx["lock"], read, integrity.adr_text, ())


@then("it reports no problem")
def no_problem(ctx: dict[str, Any]) -> None:
    assert ctx["problems"] == []


@then(parsers.parse('it names the measures vector as "{reason}"'))
def names_vector(ctx: dict[str, Any], reason: str) -> None:
    assert [p for p in ctx["problems"] if MEASURES in p and reason in p], ctx["problems"]


@then(parsers.parse('it names the GS-PAT-1 fixture as "{reason}"'))
def names_fixture(ctx: dict[str, Any], reason: str) -> None:
    assert [p for p in ctx["problems"] if FIXTURE in p and reason in p], ctx["problems"]


@then(parsers.parse('it reports "{adr}" as "{reason}"'))
def reports_adr(ctx: dict[str, Any], adr: str, reason: str) -> None:
    assert [p for p in ctx["problems"] if adr in p and reason in p], ctx["problems"]


@then(parsers.parse('it reports the problem "{text}"'))
def reports(ctx: dict[str, Any], text: str) -> None:
    assert [p for p in ctx["problems"] if text in p], ctx["problems"]
