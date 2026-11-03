"""Binds tests/features/atomic_breakdown.feature (QA-DOR-CHECK, PRC-7.1): the check run as a
process, as the ci.yml doc-check job runs it, on a copy of the real current sprint's breakdown with
one planted break per scenario."""

from __future__ import annotations

from pathlib import Path

import pytest
from atomic_breakdown_fixtures import (
    blank_cell,
    current_breakdown,
    drop_negative_examples,
    rename_id,
    run_check,
)
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("atomic_breakdown.feature")


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    return {"copy": tmp_path / "requirements-breakdown.md"}


@given("a copy of the current sprint's requirements breakdown")
def copy(ctx: dict) -> None:
    ctx["copy"].write_text(current_breakdown().read_text())


@given(parsers.parse('the NFR row "{row}" with an empty "{column}" cell'))
def empty_cell(ctx: dict, row: str, column: str) -> None:
    ctx["copy"].write_text(blank_cell(ctx["copy"].read_text(), row, column))


@given(parsers.parse('the FR rule "{rule}" without its negative Example'))
def no_negative(ctx: dict, rule: str) -> None:
    ctx["copy"].write_text(drop_negative_examples(ctx["copy"].read_text(), rule))


@given(parsers.parse('the item id "{old}" rewritten as "{new}"'))
def bad_id(ctx: dict, old: str, new: str) -> None:
    ctx["copy"].write_text(rename_id(ctx["copy"].read_text(), old, new))


@when("the atomic-breakdown check runs on the copy")
def run(ctx: dict) -> None:
    ctx["proc"] = run_check(str(ctx["copy"]))


@then(parsers.parse('the check exits 1 naming "{item}" and "{word}"'))
def fails(ctx: dict, item: str, word: str) -> None:
    out = ctx["proc"].stdout + ctx["proc"].stderr
    assert ctx["proc"].returncode == 1, out
    lines = [ln for ln in out.splitlines() if ln.startswith("FAIL") and item in ln]
    assert any(word in ln for ln in lines), out


@then(parsers.parse('the check exits 0 with "{text}"'))
def passes(ctx: dict, text: str) -> None:
    out = ctx["proc"].stdout + ctx["proc"].stderr
    assert ctx["proc"].returncode == 0, out
    assert text in out, out
