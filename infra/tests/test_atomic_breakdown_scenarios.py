"""Binds tests/features/atomic_breakdown.feature (QA-DOR-CHECK, PRC-7.1): the check run as a
process, as the ci.yml doc-check job runs it, on a copy of the real current sprint's breakdown with
one planted break per scenario, in rows picked from that breakdown (no fixed sprint ids)."""

from __future__ import annotations

from pathlib import Path

import pytest
from atomic_breakdown_fixtures import (
    blank_cell,
    current_breakdown,
    drop_negative_examples,
    first_fr_rule_with_negative,
    first_nfr_row_with,
    first_prc_id,
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


_COLUMNS = ("Metric and unit", "Method", "Target", "Test level")


@given(
    parsers.parse('the first NFR row with all four attribute cells, with an empty "{column}" cell')
)
def empty_cell(ctx: dict, column: str) -> None:
    text = ctx["copy"].read_text()
    ctx["item"] = first_nfr_row_with(text, _COLUMNS)
    ctx["copy"].write_text(blank_cell(text, ctx["item"], column))


@given("the first FR rule that has a negative Example, without its negative Example")
def no_negative(ctx: dict) -> None:
    text = ctx["copy"].read_text()
    ctx["item"] = first_fr_rule_with_negative(text)
    ctx["copy"].write_text(drop_negative_examples(text, ctx["item"]))


@given("the first PRC item id rewritten without its hyphen")
def bad_id(ctx: dict) -> None:
    text = ctx["copy"].read_text()
    old = first_prc_id(text)
    ctx["item"] = old.replace("-", "", 1)
    ctx["copy"].write_text(rename_id(text, old, ctx["item"]))


@when("the atomic-breakdown check runs on the copy")
def run(ctx: dict) -> None:
    ctx["proc"] = run_check(str(ctx["copy"]))


@then(parsers.parse('the check exits 1 naming the planted item and "{word}"'))
def fails(ctx: dict, word: str) -> None:
    out = ctx["proc"].stdout + ctx["proc"].stderr
    assert ctx["proc"].returncode == 1, out
    lines = [ln for ln in out.splitlines() if ln.startswith("FAIL") and ctx["item"] in ln]
    assert any(word in ln for ln in lines), out


@then(parsers.parse('the check exits 0 with "{text}"'))
def passes(ctx: dict, text: str) -> None:
    out = ctx["proc"].stdout + ctx["proc"].stderr
    assert ctx["proc"].returncode == 0, out
    assert text in out, out
