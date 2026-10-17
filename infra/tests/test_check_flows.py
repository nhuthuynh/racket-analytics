"""PD-4 unit tests: the DR-04 decider-cell check in docs/design/tools/check_flows.py.

Regression for review finding PE-PD4-01: the check counted any ISO date anywhere in a decider's
row, so the Opened and Due columns made a "pending" cell pass. A decider cell counts only when
the Cell column itself holds a verdict (accept or reject) with an ISO date. A row that is only
opened (dated Opened column, pending cell) is reported by ``--opened``, never by ``--decider``.
Negative cases first.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

TOOL = REPO_ROOT / "docs" / "design" / "tools" / "check_flows.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_flows", TOOL)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_flows"] = module
    spec.loader.exec_module(module)
    return module


cf = _load()

HEAD = (
    "## 14. Design review record (DR-04)\n\n"
    "| Role | Items | Opened | Due | Cell |\n"
    "|---|---|---|---|---|\n"
)


def _doc(*rows: str) -> str:
    return HEAD + "".join(f"{r}\n" for r in rows) + "\n## 15. Next\n"


ROLE = "security-privacy-engineer"


# --- negative cases first -------------------------------------------------------------------


def test_pending_cell_with_dated_opened_and_due_columns_fails():
    text = _doc(f"| {ROLE} | R4-4 | 2026-10-17 | 2026-10-18 | pending |")
    assert cf.missing_cells(text, "DR-04", [ROLE]) == [
        f"FAIL cell: DR-04 has no dated decider cell for {ROLE}"
    ]


def test_verdict_without_a_date_fails():
    text = _doc(f"| {ROLE} | R4-4 | 2026-10-17 | 2026-10-18 | accept: outbox holds ids only |")
    assert len(cf.missing_cells(text, "DR-04", [ROLE])) == 1


def test_date_without_a_verdict_fails():
    text = _doc(f"| {ROLE} | R4-4 | 2026-10-17 | 2026-10-18 | seen 2026-10-18 |")
    assert len(cf.missing_cells(text, "DR-04", [ROLE])) == 1


def test_missing_row_fails_both_checks():
    text = _doc("| product-manager | R4-2 | 2026-10-17 | 2026-10-18 | pending |")
    assert len(cf.missing_cells(text, "DR-04", [ROLE])) == 1
    assert cf.unopened_rows(text, "DR-04", [ROLE]) == [
        f"FAIL opened: DR-04 has no row with a dated Opened column for {ROLE}"
    ]


def test_opened_row_without_opened_date_fails():
    text = _doc(f"| {ROLE} | R4-4 | — | 2026-10-18 | pending |")
    assert len(cf.unopened_rows(text, "DR-04", [ROLE])) == 1


def test_section_without_cell_column_fails():
    text = (
        "## DR-04\n\n| Role | Items | Opened |\n|---|---|---|\n"
        f"| {ROLE} | R4-4 | 2026-10-17 |\n"
    )
    assert cf.missing_cells(text, "DR-04", [ROLE]) == [
        "FAIL review: DR-04 has no decider table with a 'Cell' column"
    ]


def test_cli_pending_cell_exits_1(tmp_path: Path, capsys):
    f = tmp_path / "flows.md"
    f.write_text(_doc(f"| {ROLE} | R4-4 | 2026-10-17 | 2026-10-18 | pending |"))
    assert cf.main([str(f), "--review", "DR-04", "--decider", ROLE]) == 1
    assert "check-flows: 1 problem(s)" in capsys.readouterr().out


# --- positive cases -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cell",
    [
        "accept (2026-10-18): outbox holds ids only",
        "security-privacy-engineer: **reject** (2026-10-18): consent default",
        "accept (2026-10-17, author)",
    ],
)
def test_dated_verdict_in_cell_column_passes(cell: str):
    text = _doc(f"| {ROLE} | R4-4 | 2026-10-17 | 2026-10-18 | {cell} |")
    assert cf.missing_cells(text, "DR-04", [ROLE]) == []


def test_opened_row_with_pending_cell_passes_opened_check():
    text = _doc(f"| {ROLE} | R4-4 | 2026-10-17 | 2026-10-18 | pending |")
    assert cf.unopened_rows(text, "DR-04", [ROLE]) == []


def test_cli_opened_only_exits_0(tmp_path: Path):
    f = tmp_path / "flows.md"
    f.write_text(_doc(f"| {ROLE} | R4-4 | 2026-10-17 | 2026-10-18 | pending |"))
    assert cf.main([str(f), "--review", "DR-04", "--opened", ROLE]) == 0
