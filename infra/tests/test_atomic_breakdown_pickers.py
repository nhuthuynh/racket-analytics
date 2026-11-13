"""PLAN-06 review round 1 (PE-PLAN06-01, QA06-PLAN-01; TCR row in
docs/sprints/06/test-change-requests.md): the QA-DOR-CHECK scenarios plant their breaks in rows
picked from the current breakdown, never in fixed sprint ids. Each picker runs on every sprint's
real breakdown, so the next plan PR cannot strand the scenarios on ids its breakdown lacks."""

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
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

COLUMNS = ("Metric and unit", "Method", "Target", "Test level")
BREAKDOWNS = sorted((REPO_ROOT / "docs" / "sprints").glob("[0-9][0-9]/requirements-breakdown.md"))


def _ids(paths: list[Path]) -> list[str]:
    return [p.parent.name for p in paths]


def test_there_is_a_breakdown_per_sprint_and_the_current_one_is_among_them() -> None:
    assert len(BREAKDOWNS) >= 2
    assert current_breakdown() in BREAKDOWNS


@pytest.mark.parametrize("path", BREAKDOWNS, ids=_ids(BREAKDOWNS))
def test_the_nfr_picker_finds_a_row_with_all_four_attribute_cells(path: Path) -> None:
    text = path.read_text()
    row = first_nfr_row_with(text, COLUMNS)
    assert row.startswith("NFR-")
    for column in COLUMNS:
        assert blank_cell(text, row, column) != text


@pytest.mark.parametrize("path", BREAKDOWNS, ids=_ids(BREAKDOWNS))
def test_the_fr_picker_finds_a_rule_with_a_negative_example(path: Path) -> None:
    text = path.read_text()
    rule = first_fr_rule_with_negative(text)
    assert rule.startswith("FR-")
    assert drop_negative_examples(text, rule) != text


@pytest.mark.parametrize("path", BREAKDOWNS, ids=_ids(BREAKDOWNS))
def test_the_prc_picker_finds_an_id_row(path: Path) -> None:
    text = path.read_text()
    item = first_prc_id(text)
    assert item.startswith("PRC-")
    assert rename_id(text, item, item.replace("-", "", 1)) != text


@pytest.mark.parametrize("path", BREAKDOWNS, ids=_ids(BREAKDOWNS))
def test_each_planted_break_turns_the_check_red_on_every_sprint(path: Path, tmp_path: Path) -> None:
    text = path.read_text()
    row = first_nfr_row_with(text, COLUMNS)
    rule = first_fr_rule_with_negative(text)
    item = first_prc_id(text)
    planted = [
        (blank_cell(text, row, "Method"), row, "method"),
        (drop_negative_examples(text, rule), rule, "negative"),
        (rename_id(text, item, item.replace("-", "", 1)), item.replace("-", "", 1), "id"),
    ]
    for body, name, word in planted:
        copy = tmp_path / "requirements-breakdown.md"
        copy.write_text(body)
        proc = run_check(str(copy))
        out = proc.stdout + proc.stderr
        assert proc.returncode == 1, out
        fails = [ln for ln in out.splitlines() if ln.startswith("FAIL")]
        assert any(name in ln and word in ln for ln in fails), out


def test_the_pickers_refuse_a_breakdown_without_a_matching_item() -> None:
    with pytest.raises(AssertionError, match="no NFR row"):
        first_nfr_row_with("| Id | Metric and unit |\n|---|---|\n| NFR-1.1 | x |\n", COLUMNS)
    with pytest.raises(AssertionError, match="no FR rule"):
        first_fr_rule_with_negative("Rule: FR-100.R1 x\n  Example: y (happy)\n")
    with pytest.raises(AssertionError, match="no PRC id"):
        first_prc_id("| Id | Rule |\n|---|---|\n| NFR-1.1 | x |\n")
