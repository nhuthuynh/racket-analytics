"""PD-4b unit tests for docs/design/tools/check_flows.py, negative cases first. PE-PD4-01: only
the Cell column counts (a pending cell with dated Opened/Due fails; ``--opened`` proves opened).
PE-PD4-05: the cell must open with ``[role:] [**]accept|reject[**] (date``. SFE-PD4-07: one row
per role, so a pending row cannot hide behind a decided one. PE-PD4b-01 / SFE-PD4b-01: the link
and state-row checks each have a test that fails when the check is removed."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

TOOL = REPO_ROOT / "docs" / "design" / "tools" / "check_flows.py"


_spec = importlib.util.spec_from_file_location("check_flows", TOOL)
assert _spec
assert _spec.loader
cf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cf)

HEAD = (
    "## 14. Design review record (DR-04)\n\n"
    "| Role | Items | Opened | Due | Cell |\n"
    "|---|---|---|---|---|\n"
)


def _doc(*rows: str) -> str:
    return HEAD + "".join(f"{r}\n" for r in rows) + "\n## 15. Next\n"


ROLE = "security-privacy-engineer"


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


@pytest.mark.parametrize(
    "cell",
    ["pending: will accept or reject by 2026-10-18", "not accepted yet; accept (2026-10-18)"],
)
def test_cell_that_only_mentions_a_verdict_and_a_date_fails(cell: str):
    text = _doc(f"| {ROLE} | R4-4 | 2026-10-17 | 2026-10-18 | {cell} |")
    assert len(cf.missing_cells(text, "DR-04", [ROLE])) == 1


def test_two_rows_for_one_decider_fail_both_checks():
    pending = f"| {ROLE} | R4-4 | 2026-10-17 | 2026-10-18 | pending |"
    decided = f"| {ROLE} | R4-5 | 2026-10-17 | 2026-10-18 | accept (2026-10-18) |"
    expected = [f"FAIL row: DR-04 has 2 rows for {ROLE}; exactly one per role"]
    assert cf.missing_cells(_doc(decided, pending), "DR-04", [ROLE]) == expected
    assert cf.unopened_rows(_doc(pending, decided), "DR-04", [ROLE]) == expected


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
    text = f"## DR-04\n\n| Role | Items | Opened |\n|---|---|---|\n| {ROLE} | R4-4 | 2026-10-17 |\n"
    assert cf.missing_cells(text, "DR-04", [ROLE]) == [
        "FAIL review: DR-04 has no decider table with a 'Cell' column"
    ]


def test_relative_link_to_a_missing_file_fails(tmp_path: Path):
    f = tmp_path / "flows.md"
    text = "See [gone](missing.md) and [gone too](sub/absent.md#part).\n"
    assert cf.broken_links(f, text) == [
        f"FAIL link: missing.md does not resolve from {f}",
        f"FAIL link: sub/absent.md#part does not resolve from {f}",
    ]


def test_screen_without_a_state_row_fails():
    text = "| P-01 | Empty | shows the empty card |\n| P-02 | Loading | spinner |\n"
    assert cf.missing_states(text, ["P-01", "P-02"], ["Empty", "Loading"]) == [
        "FAIL state: P-01 has no 'Loading' row",
        "FAIL state: P-02 has no 'Empty' row",
    ]


def test_state_named_only_in_prose_or_another_column_fails():
    text = "P-01 Error is described in prose.\n| P-02 | P-01 | Error |\n|  P-01 | Error |\n"
    assert cf.missing_states(text, ["P-01"], ["Error"]) == ["FAIL state: P-01 has no 'Error' row"]


def test_cli_broken_link_and_missing_state_exit_1(tmp_path: Path, capsys):
    f = tmp_path / "flows.md"
    f.write_text("[x](nowhere.md)\n| P-01 | Empty | ok |\n")
    args = [str(f), "--review", "DR-04", "--screen", "P-01", "--states", "Empty,Error"]
    assert cf.main(args) == 1
    out = capsys.readouterr().out
    assert "FAIL link: nowhere.md" in out
    assert "FAIL state: P-01 has no 'Error' row" in out
    assert "check-flows: 2 problem(s)" in out


def test_cli_pending_cell_exits_1(tmp_path: Path, capsys):
    f = tmp_path / "flows.md"
    f.write_text(_doc(f"| {ROLE} | R4-4 | 2026-10-17 | 2026-10-18 | pending |"))
    assert cf.main([str(f), "--review", "DR-04", "--decider", ROLE]) == 1
    assert "check-flows: 1 problem(s)" in capsys.readouterr().out


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


def test_external_links_and_anchors_are_skipped_and_section_links_resolve(tmp_path: Path):
    (tmp_path / "other.md").write_text("# Other\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.md").write_text("# Deep\n")
    f = tmp_path / "flows.md"
    text = (
        "[web](https://example.com/x.md) [mail](mailto:a@example.com) [top](#states) "
        "[file](other.md) [section](other.md#section) [nested](sub/deep.md#a-b)\n"
    )
    assert cf.broken_links(f, text) == []


def test_screen_with_every_state_row_passes():
    text = "| P-01 | Empty | card |\n| P-01 | Loading | spinner |\n"
    assert cf.missing_states(text, ["P-01"], ["Empty", "Loading"]) == []
