"""S3-DoD-P6 tally (FIX-03-1b; sprint-03 §9.1; NFR-027 b; PO P12 option b).

The manual screen-reader pass needs a human tester with an iPhone (VoiceOver) and an Android
phone (TalkBack); the agents have neither (P6). The row's status is therefore counted from the
result cells of docs/sprints/03/a11y-manual.md §3, and the sprint plan must say the same.

Negative cases first: a manual without rows, with a gap or a duplicate in its numbering, or a
cell that is neither a result nor "not run" never reads as met (fail closed, ADR 0014).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys

import pytest
from a11y_manual_fixtures import HEAD, TAIL, manual, sprint_plan
from conftest import REPO_ROOT, SCRIPTS_DIR

MEASURE = SCRIPTS_DIR / "measure"
SCRIPT = MEASURE / "a11y_manual.py"
MANUAL = REPO_ROOT / "docs" / "sprints" / "03" / "a11y-manual.md"
PLAN = REPO_ROOT / "docs" / "sprints" / "sprint-03.md"


def _load():
    spec = importlib.util.spec_from_file_location("a11y_manual", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["a11y_manual"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def m():
    return _load()


# --- unit: negative cases first -------------------------------------------------------------


@pytest.mark.unit
def test_a_manual_without_a_result_table_is_refused(m) -> None:
    with pytest.raises(ValueError, match="no result table"):
        m.tally("## 3. Script and results\n\nNothing.\n\n## 4. Result\n")


@pytest.mark.unit
def test_a_gap_in_the_row_numbers_is_refused(m) -> None:
    with pytest.raises(ValueError, match="expected 4"):
        m.tally(manual(4, ids=["1", "2", "3", "5"]))


@pytest.mark.unit
def test_a_duplicate_row_number_is_refused(m) -> None:
    with pytest.raises(ValueError, match="row 2 is out of order"):
        m.tally(manual(3, ids=["1", "2", "2"]))


@pytest.mark.unit
def test_a_cell_that_is_neither_a_result_nor_not_run_is_refused(m) -> None:
    text = manual(2).replace("| 2 | screen 2 | not run |", "| 2 | screen 2 | looked fine |")
    with pytest.raises(ValueError, match=r"row 2.*looked fine"):
        m.tally(text)


@pytest.mark.unit
def test_a_range_row_counts_every_row_it_covers(m) -> None:
    text = manual(2, ids=["1-24", "25"])
    assert m.tally(text)["rows"] == 25


@pytest.mark.unit
def test_a_range_row_with_a_result_counts_all_its_rows_as_run(m) -> None:
    text = manual(2, voiceover=1, talkback=1, ids=["1-24", "25"])
    t = m.tally(text)
    assert (t["voiceover"], t["talkback"], t["status"]) == (
        24,
        24,
        "not met: waiting on P6 (24 of 25 rows run)",
    )


def _range_manual(voiceover: str, talkback: str, rest: str = "pass") -> str:
    """Rows 1-24 as one range row with the given cells, then rows 25-38 with `rest` on both."""
    lines = [f"| 1-24 | earlier screens | {voiceover} | {talkback} |"]
    lines += [f"| {n} | screen {n} | {rest} | {rest} |" for n in range(25, 39)]
    return HEAD + "\n".join(lines) + "\n" + TAIL


# PE-R1-01 / SBE-FIX031b-R1-01: a range row's partial count must never read as the whole range.


@pytest.mark.unit
def test_a_range_row_with_a_partial_count_counts_only_the_rows_run(m) -> None:
    t = m.tally(_range_manual("pass (3 of 24)", "pass (3 of 24)"))
    assert (t["voiceover"], t["talkback"], t["met"]) == (17, 17, False)
    assert t["status"].startswith("not met: waiting on P6")


@pytest.mark.unit
def test_partial_counts_on_both_readers_count_only_rows_proven_run_on_both(m) -> None:
    # 3 of 24 on VoiceOver and 1 of 24 on TalkBack need not be the same rows: none is proven.
    t = m.tally(_range_manual("pass (3 of 24)", "fail: one (1 of 24)", rest="not run"))
    assert (t["voiceover"], t["talkback"], t["both"]) == (3, 1, 0)
    assert t["status"] == "not met: waiting on P6 (0 of 38 rows run)"


@pytest.mark.unit
def test_a_range_row_with_a_full_count_counts_every_row(m) -> None:
    t = m.tally(_range_manual("pass (24 of 24)", "fail: one heading skipped (24 of 24)"))
    assert t["status"] == "met (38 of 38 rows run)"


@pytest.mark.unit
@pytest.mark.parametrize(
    "cell",
    ["pass (3 of 20)", "pass (0 of 24)", "pass (25 of 24)", "not run (2 of 24)"],
)
def test_a_count_that_does_not_fit_the_row_is_refused(m, cell: str) -> None:
    with pytest.raises(ValueError, match="row 1-24"):
        m.tally(_range_manual(cell, "pass"))


@pytest.mark.unit
@pytest.mark.parametrize("cell", ["passive", "failed to start", "fail", "fail:", "passed", "pass!"])
def test_a_cell_outside_pass_fail_words_not_run_is_refused(m, cell: str) -> None:
    text = manual(2, voiceover=2, talkback=2).replace(
        "| 2 | screen 2 | pass |", f"| 2 | screen 2 | {cell} |"
    )
    with pytest.raises(ValueError, match="row 2"):
        m.tally(text)


@pytest.mark.unit
@pytest.mark.parametrize("cell", ["failover", "passive voice not read"])
def test_a_result_word_without_a_word_boundary_is_refused(m, cell: str) -> None:
    text = manual(1, voiceover=1, talkback=1).replace(
        "| 1 | screen 1 | pass |", f"| 1 | screen 1 | {cell} |"
    )
    with pytest.raises(ValueError, match="row 1"):
        m.tally(text)


# PE-R2-01: a "fail:" cell whose only "words" are the count heard nothing; it is malformed,
# never a full range run.


@pytest.mark.unit
@pytest.mark.parametrize(
    "cell", ["fail: (3 of 24)", "fail:(3 of 24)", "fail: (24 of 24)", "FAIL: ( 3 of 24 )"]
)
def test_a_fail_cell_with_only_a_count_and_no_words_heard_is_refused(m, cell: str) -> None:
    with pytest.raises(ValueError, match="row 1-24"):
        m.tally(_range_manual(cell, cell))


@pytest.mark.unit
def test_a_count_with_extra_spaces_is_still_read_as_the_count(m) -> None:
    t = m.tally(_range_manual("fail: x ( 3 of 24 )", "pass (3  of 24)", rest="not run"))
    assert (t["voiceover"], t["talkback"], t["both"]) == (3, 3, 0)
    assert t["status"] == "not met: waiting on P6 (0 of 38 rows run)"


@pytest.mark.integration
def test_a_fail_cell_with_only_a_count_exits_2_as_malformed(tmp_path) -> None:
    path = tmp_path / "m.md"
    path.write_text(_range_manual("fail: (3 of 24)", "fail: (3 of 24)"))
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, timeout=60
    )
    assert out.returncode == 2, out.stdout + out.stderr
    assert "row 1-24" in out.stderr


# PE-R3-01 / SBE-R3-01 / SBE-FIX031b-R2-01 / PE-70-02: a count anywhere inside the words heard
# (not only a lone count) is malformed; it must never read as a full range run.

COUNT_IN_WORDS = [
    "fail: (3 of 24) back button not read",
    "fail: (3 of 24).",
    "fail: x (3 of 24) y",
    "fail: label not read (3 of 24).",
    "fail: heard (1 of 24) then stop",
    "fail: (1 of 24) nothing",
]


@pytest.mark.unit
@pytest.mark.parametrize("cell", COUNT_IN_WORDS)
def test_a_count_inside_the_words_heard_is_refused(m, cell: str) -> None:
    with pytest.raises(ValueError, match="row 1-24"):
        m.tally(_range_manual(cell, cell))


@pytest.mark.integration
@pytest.mark.parametrize("cell", COUNT_IN_WORDS[:2])
def test_a_count_inside_the_words_heard_exits_2_as_malformed(tmp_path, cell: str) -> None:
    path = tmp_path / "m.md"
    path.write_text(_range_manual(cell, cell))
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, timeout=60
    )
    assert out.returncode == 2, out.stdout + out.stderr
    assert "row 1-24" in out.stderr


@pytest.mark.unit
def test_words_heard_that_merely_mention_of_are_still_words(m) -> None:
    # Only a count-shaped "(k of w)" is refused; ordinary words with "of" stay words heard.
    t = m.tally(_range_manual("fail: name of the button not read", "pass"))
    assert (t["voiceover"], t["talkback"]) == (38, 38)


# PE-70-01 / SBE-FIX031b-R2-02: a reversed range ("38-37") would have a negative width and
# make its rows disappear, so two rows "not run" read as met.


@pytest.mark.unit
@pytest.mark.parametrize("rid", ["3-2", "38-37"])
def test_a_reversed_range_row_is_refused(m, rid: str) -> None:
    text = manual(3, voiceover=3, talkback=3, ids=["1", "2", rid])
    with pytest.raises(ValueError, match=f"row {rid}"):
        m.tally(text)


@pytest.mark.integration
def test_a_reversed_range_row_exits_2_as_malformed(tmp_path) -> None:
    lines = [f"| {n} | screen {n} | pass | pass |" for n in range(1, 37)]
    lines.append("| 38-37 | last two | not run | not run |")
    path = tmp_path / "m.md"
    path.write_text(HEAD + "\n".join(lines) + "\n" + TAIL)
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, timeout=60
    )
    assert out.returncode == 2, out.stdout + out.stderr
    assert "row 38-37" in out.stderr


# PE-70-03 / SBE-FIX031b-R2-03: a row id that cannot be read, or a section-3 table whose
# header does not name both screen readers exactly, is malformed, not silently skipped.


@pytest.mark.unit
@pytest.mark.parametrize("rid", ["**3**", "3.", "38a", "row 3"])
def test_a_row_id_that_cannot_be_read_is_refused(m, rid: str) -> None:
    text = manual(3, ids=["1", "2", rid])
    with pytest.raises(ValueError, match="cannot be read"):
        m.tally(text)


@pytest.mark.unit
def test_a_table_header_without_both_screen_readers_is_refused(m) -> None:
    variant = manual(2).replace(
        "| # | Screen / state | VoiceOver iOS | TalkBack Android |",
        "| # | Screen / state | VoiceOver iOS | TalkBack (Android) |",
    )
    with pytest.raises(ValueError, match="VoiceOver iOS and TalkBack Android"):
        m.tally(variant)


@pytest.mark.unit
def test_a_second_table_with_a_header_variant_is_refused(m) -> None:
    extra = (
        "\n\n| # | Screen | Steps | Expected | VoiceOver | TalkBack Android |\n"
        "|---|---|---|---|---|---|\n"
        "| 3 | s | step | exp | not run | not run |\n"
    )
    text = manual(2, voiceover=2, talkback=2).replace(TAIL, extra + TAIL)
    with pytest.raises(ValueError, match="VoiceOver iOS and TalkBack Android"):
        m.tally(text)


@pytest.mark.unit
def test_an_expected_row_count_that_differs_is_refused(m) -> None:
    with pytest.raises(ValueError, match="37 rows, expected 38"):
        m.tally(manual(37, voiceover=37, talkback=37), expected_rows=38)
    assert m.tally(manual(38), expected_rows=38)["rows"] == 38


@pytest.mark.integration
def test_rows_option_exits_2_when_the_manual_lost_a_row(tmp_path) -> None:
    path = tmp_path / "m.md"
    path.write_text(manual(37, voiceover=37, talkback=37))
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(path), "--rows", "38"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert out.returncode == 2, out.stdout + out.stderr
    assert "expected 38" in out.stderr


@pytest.mark.unit
def test_a_row_with_fewer_cells_than_the_header_is_refused(m) -> None:
    text = manual(2).replace("| 2 | screen 2 | not run | not run |", "| 2 | short |")
    with pytest.raises(ValueError, match="row 2 has 2 cells"):
        m.tally(text)


@pytest.mark.integration
def test_a_short_row_exits_2_as_malformed(tmp_path) -> None:
    path = tmp_path / "m.md"
    path.write_text(manual(2).replace("| 2 | screen 2 | not run | not run |", "| 2 | y |"))
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, timeout=60
    )
    assert out.returncode == 2, out.stdout + out.stderr
    assert "row 2 has 2 cells" in out.stderr


@pytest.mark.unit
def test_not_met_counts_rows_run_on_both_screen_readers(m) -> None:
    t = m.tally(manual(38, voiceover=38, talkback=10))
    assert t["status"] == "not met: waiting on P6 (10 of 38 rows run)"
    assert t["met"] is False


@pytest.mark.unit
def test_met_needs_every_row_on_both_screen_readers(m) -> None:
    t = m.tally(manual(38, voiceover=38, talkback=38))
    assert t["status"] == "met (38 of 38 rows run)"
    assert t["met"] is True


@pytest.mark.unit
def test_a_plan_without_the_dod_row_is_refused(m) -> None:
    with pytest.raises(ValueError, match="S3-DoD-P6"):
        m.dod_status("### 9.1\n\nno table\n")


@pytest.mark.unit
def test_the_dod_status_cell_is_read_without_emphasis(m) -> None:
    plan = sprint_plan("**not met: waiting on P6** (0 of 38 rows run)")
    assert m.dod_status(plan) == "not met: waiting on P6 (0 of 38 rows run)"


# --- integration: the repository's own manual and sprint plan --------------------------------


@pytest.mark.integration
def test_the_repository_manual_and_sprint_plan_agree_on_s3_dod_p6() -> None:
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(MANUAL), "--dod", str(PLAN)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    # rc 0 = met, 1 = not met; 2 (malformed) and 3 (plan disagrees with the manual) are failures.
    assert out.returncode in (0, 1), out.stdout + out.stderr
    assert '"rows": 38' in out.stdout


@pytest.mark.integration
def test_the_repository_manual_has_exactly_38_rows_with_the_rows_option() -> None:
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(MANUAL), "--dod", str(PLAN), "--rows", "38"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert out.returncode in (0, 1), out.stdout + out.stderr
    assert '"rows": 38' in out.stdout
