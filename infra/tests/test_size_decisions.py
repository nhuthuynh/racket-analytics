"""SIZE-WAIVERS-03 unit tests: the size-decision rules of scripts/ci/size_decisions.py.

A ticket's size decision is a stack of PRs. Each PR is either waived up to a recorded number
(it gets the `size-waiver` label) or a stacked part that must pass `PR size` unlabelled, so at
most 400 changed lines (ADR 0039 rule 4, ADR 0030 rule 4). Pure: no git, no files.
"""

from __future__ import annotations

import importlib.util
import sys

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit
SCRIPT = SCRIPTS_DIR / "ci" / "size_decisions.py"
_spec = importlib.util.spec_from_file_location("size_decisions", SCRIPT)
assert _spec is not None
assert _spec.loader is not None
sd = importlib.util.module_from_spec(_spec)
sys.modules["size_decisions"] = sd
_spec.loader.exec_module(sd)

TABLE = """\
# x

## Size decisions

| Ticket | Measured | PRs, in stack order | Kind |
|---|---|---|---|
| T-WAIVED | 1462 | waived 1502 | waived |
| T-STACKED | 575 | 355; 382 | stacked |

## Rows
| T-IGNORED | 9 | 9 | not in the decisions table |
"""


def decisions() -> dict:
    return sd.parse(TABLE)


# ---------------------------------------------------------------- negative cases first
def test_a_part_that_is_neither_a_number_nor_a_waiver_is_refused() -> None:
    with pytest.raises(ValueError, match="T-BAD"):
        sd.parse(TABLE.replace("| 355; 382 |", "| 355; about 300 |").replace("T-STACKED", "T-BAD"))


def test_a_file_without_the_decisions_table_is_refused() -> None:
    with pytest.raises(ValueError, match="Size decisions"):
        sd.parse("# nothing here\n")


def test_a_ticket_in_scope_without_a_decision_is_a_problem() -> None:
    found = sd.problems(decisions(), {"T-WAIVED": 1462, "T-MISSING": 500})
    assert found == ["T-MISSING: no size decision (500 changed lines measured)"]


def test_an_unwaived_part_over_400_is_a_problem() -> None:
    d = sd.parse(TABLE.replace("355; 382", "401; 214"))
    assert sd.problems(d, {"T-STACKED": 575}) == [
        "T-STACKED: PR 1 is 401 lines, over 400, without a waiver"
    ]


def test_parts_that_leave_no_room_for_the_tickets_decisions_file_are_a_problem() -> None:
    # SQA-1 (PR #6): each ticket PR also adds docs/sprints/03/decisions/<ID>.md, which the gate
    # counts; a cap set at the measured code lines alone fails when that PR opens.
    d = sd.parse(TABLE.replace("waived 1502", "waived 1462"))
    assert sd.problems(d, {"T-WAIVED": 1462}) == [
        "T-WAIVED: the PRs cover 1462 of 1502 changed lines"
        " (1462 measured + 40 for its decisions file)"
    ]


def test_parts_that_do_not_cover_the_measured_lines_are_a_problem() -> None:
    assert sd.problems(decisions(), {"T-WAIVED": 1463}) == [
        "T-WAIVED: the PRs cover 1502 of 1503 changed lines"
        " (1463 measured + 40 for its decisions file)"
    ]


def test_a_waived_pr_above_its_recorded_number_needs_a_new_row() -> None:
    v = sd.apply(decisions(), "T-WAIVED", 1, 1503)
    assert v.label is None
    assert v.new_row_needed
    assert "1503" in v.reason
    assert "1502" in v.reason


def test_a_stacked_part_above_400_needs_a_new_row() -> None:
    v = sd.apply(decisions(), "T-STACKED", 2, 401)
    assert (v.label, v.new_row_needed) == (None, True)


def test_a_ticket_or_pr_without_a_decision_needs_a_new_row() -> None:
    assert sd.apply(decisions(), "T-NONE", 1, 10).new_row_needed
    assert sd.apply(decisions(), "T-STACKED", 3, 10).new_row_needed
    assert sd.apply(decisions(), "T-STACKED", 0, 10).new_row_needed


# ---------------------------------------------------------------- positive
def test_the_decisions_table_is_read_in_stack_order() -> None:
    assert decisions() == {
        "T-WAIVED": (sd.Part(cap=1502, waived=True),),
        "T-STACKED": (sd.Part(cap=355, waived=False), sd.Part(cap=382, waived=False)),
    }


def test_a_complete_decisions_table_has_no_problems() -> None:
    assert sd.problems(decisions(), {"T-WAIVED": 1462, "T-STACKED": 575}) == []


def test_a_waived_pr_within_its_number_gets_the_label() -> None:
    v = sd.apply(decisions(), "T-WAIVED", 1, 1502)
    assert (v.label, v.new_row_needed) == ("size-waiver", False)


def test_a_stacked_part_within_400_gets_no_label() -> None:
    v = sd.apply(decisions(), "T-STACKED", 2, 400)
    assert (v.label, v.new_row_needed) == (None, False)
