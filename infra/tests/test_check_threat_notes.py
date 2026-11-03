"""SEC-5 unit tests for docs/security/tools/check_threat_notes.py, negative cases first.

An "Accepted residual" threat row must name an ADR id (``ADR 0023`` or a link to
``decisions/0023-...md``) that resolves to an ADR whose status is Accepted, because risk
acceptance needs a human decider recorded in an ADR (NFR-050.9, P19; kickoff SEC-3 item).
T5-* rows (Sprint 5) get the same row checks as T4-* rows.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

TOOL = REPO_ROOT / "docs" / "security" / "tools" / "check_threat_notes.py"

_spec = importlib.util.spec_from_file_location("check_threat_notes", TOOL)
assert _spec
assert _spec.loader
ctn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ctn)


def _row(tid: str, source: str, status: str = "Accepted residual") -> str:
    return f"| {tid} | I | threat | control | {source} | ST-083 | test | {status} |\n"


@pytest.fixture
def decisions(tmp_path: Path) -> Path:
    d = tmp_path / "decisions"
    d.mkdir()
    (d / "0101-accepted-residuals.md").write_text(
        "# 0101. Residuals\n\n- **Status:** Accepted\n- **Date:** 2026-11-03\n", encoding="utf-8"
    )
    (d / "0102-proposed-residuals.md").write_text(
        "# 0102. Residuals\n\n- **Status:** Proposed (PO decides, P19)\n", encoding="utf-8"
    )
    return d


def test_planted_accepted_residual_row_without_an_adr_id_fails(decisions: Path):
    text = _row("T5-UT-9", "judgment; NFR-070")
    assert ctn.unaccepted_residuals(text, decisions) == [
        "FAIL residual: T5-UT-9 is 'Accepted residual' but names no ADR id"
    ]


def test_bold_accepted_residual_status_is_still_checked(decisions: Path):
    assert (
        len(ctn.unaccepted_residuals(_row("T4-RT-5", "14.2.1", "**Accepted residual**"), decisions))
        == 1
    )


def test_adr_id_that_does_not_exist_fails(decisions: Path):
    assert ctn.unaccepted_residuals(_row("T5-BK-9", "ADR 0999"), decisions) == [
        "FAIL residual: T5-BK-9 names ADR 0999, which is not an Accepted ADR in decisions"
    ]


def test_adr_that_is_only_proposed_fails(decisions: Path):
    assert ctn.unaccepted_residuals(_row("T5-BK-9", "ADR 0102"), decisions) == [
        "FAIL residual: T5-BK-9 names ADR 0102, which is not an Accepted ADR in decisions"
    ]


def test_three_digit_number_is_not_an_adr_id(decisions: Path):
    assert len(ctn.unaccepted_residuals(_row("T5-BK-9", "ADR 101"), decisions)) == 1


@pytest.mark.parametrize(
    "source",
    [
        "ADR 0101",
        "ADR-0101",
        "[ADR 0101](../decisions/0101-accepted-residuals.md)",
        "[0101](x/0101-a.md)",
    ],
)
def test_accepted_adr_by_id_or_link_passes(decisions: Path, source: str):
    assert ctn.unaccepted_residuals(_row("T5-BK-9", source), decisions) == []


def test_one_accepted_adr_among_several_ids_is_enough(decisions: Path):
    assert ctn.unaccepted_residuals(_row("T5-BK-9", "ADR 0102; ADR 0101"), decisions) == []


@pytest.mark.parametrize("status", ["D", "O (SEC-S5-TM-01)", "Residual, waiting on P19", "C"])
def test_rows_that_are_not_accepted_residuals_need_no_adr(decisions: Path, status: str):
    assert ctn.unaccepted_residuals(_row("T5-BK-9", "judgment", status), decisions) == []


def test_t5_rows_get_the_eight_cell_check():
    text = "| T5-OB-1 | I | threat | control | src | ST-075a | test |\n"
    assert ctn.bad_threat_rows(text) == [
        "FAIL threat: T5-OB-1 needs 8 cells with a Test and a Status"
    ]


def test_default_decisions_dir_is_the_repository_one():
    assert ctn.DECISIONS == REPO_ROOT / "docs" / "decisions"
