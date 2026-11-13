"""CLI binding of tests/features/reference_set.feature (ST-170a; FR-170.R1-R3; ADR 0061).

Each scenario builds a reference tree in a temporary folder and runs ``racket-reference-lint``
over it with the repository's pattern catalogue and sources register. Written red first: the
lint does not exist before ST-170a, so an entry with no source "passes" because nothing checks it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support.references import (
    LINT,
    SET,
    SOURCES,
    entry,
    lint_args,
    reference_doc,
    write_version,
)

scenarios("reference_set.feature")


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "references", "entry": entry()}


def _write(ctx: dict[str, Any], lock: bool = True) -> None:
    write_version(ctx["root"], reference_doc([ctx["entry"]]), lock=lock)


@given(parsers.parse('reference set "{name}" v1 with an AN-09 entry citing "{cid}"'))
def set_citing(ctx: dict[str, Any], name: str, cid: str) -> None:
    assert name == SET
    ctx["entry"] = entry(source={"citation_id": cid})
    _write(ctx)


@given(parsers.parse('reference set "{name}" v1 with an AN-09 entry measured on footage "{fid}"'))
def set_measured(ctx: dict[str, Any], name: str, fid: str) -> None:
    assert name == SET
    ctx["entry"] = entry(
        source_type="measured",
        source={"footage_id": fid, "rights_record_id": "RR-0001"},
        value=0.55,
        n=40,
        k=22,
        band=[0.45, 0.70],
    )
    _write(ctx)


@given(parsers.parse('"{cid}" is a row of the sources register'))
def is_a_row(cid: str) -> None:
    assert f"| {cid} |" in SOURCES.read_text(encoding="utf-8")


@given(parsers.parse('the entry has no "{field}"'))
def without(ctx: dict[str, Any], field: str) -> None:
    ctx["entry"].pop(field)
    _write(ctx)


@given(parsers.parse('the entry\'s "{field}" is "{value}"'))
def with_value(ctx: dict[str, Any], field: str, value: str) -> None:
    ctx["entry"][field] = value
    _write(ctx)


@given("v2 of the set changes the AN-09 band and is locked")
def v2_locked(ctx: dict[str, Any]) -> None:
    write_version(ctx["root"], reference_doc([entry(band=[0.40, 0.65])], version=2))


@given("v1 is edited in place after it was locked")
def v1_edited(ctx: dict[str, Any]) -> None:
    path = ctx["root"] / SET / "v1.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["entries"][0]["band"] = [0.50, 0.75]
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


@when("racket-reference-lint runs", target_fixture="result")
def run(ctx: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    capsys.readouterr()
    rc = LINT.load()(lint_args(ctx["root"]))
    out, err = capsys.readouterr()
    return int(rc), out + err


@then("it exits 0")
def exits_0(result: tuple[int, str]) -> None:
    assert result[0] == 0, result[1]


@then(parsers.parse('it exits 1 naming the entry and "{text}"'))
def exits_1_entry(ctx: dict[str, Any], result: tuple[int, str], text: str) -> None:
    rc, out = result
    assert rc == 1, out
    assert any(ctx["entry"]["id"] in line and text in line for line in out.splitlines()), out


@then(parsers.parse('it exits 1 naming "{name}" and "{text}"'))
def exits_1_name(result: tuple[int, str], name: str, text: str) -> None:
    rc, out = result
    assert rc == 1, out
    assert any(name in line and text in line for line in out.splitlines()), out
