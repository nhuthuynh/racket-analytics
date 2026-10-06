"""PE-S2-R1-03 (FR-052 "correct any rally"): a correction can set the whole outcome input in
one command, ``field = "outcome"`` with the four outcome fields as ``value``, audited as ONE
change (old and new outcome objects). One-field corrections cannot go between ``replay`` and a
scored ending: every single step is an invalid outcome (I6).

Negative first: an invalid whole outcome is refused with the same field codes as a tag; an
unchanged outcome is refused; then replay <-> scored both ways, a side swap with a responsible
player, the audit row and the undo.
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.matches.scorebook.domain import InvalidOutcome
from racket.platform.errors import ValidationFailed
from tests.unit.matches.test_scorebook_corrections import Book, fresh

pytestmark = [pytest.mark.unit, pytest.mark.scoring]

REPLAY = {"ending": "replay", "winning_side": None, "responsible_player": None, "fault_kind": None}
WIN_A = {"ending": "winner", "winning_side": "A", "responsible_player": None, "fault_kind": None}


def codes(exc: pytest.ExceptionInfo[Any]) -> list[tuple[str | None, str]]:
    return [(f.field, f.code) for f in exc.value.fields]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ({"ending": "replay", "winning_side": "A"}, [("winning_side", "replay_has_no_side")]),
        ({"ending": "winner"}, [("winning_side", "side_required")]),
        ({"ending": "winner", "winning_side": "A", "seq": 1}, [(None, "unknown_field")]),
        ("replay", [(None, "invalid")]),
        (["replay"], [(None, "invalid")]),
    ],
)
def test_an_invalid_whole_outcome_is_refused(value: Any, expected: list[Any]) -> None:
    b = fresh("A")
    with pytest.raises(InvalidOutcome) as exc:
        b.correct(1, "outcome", value)
    assert codes(exc) == expected


def test_an_unchanged_outcome_is_refused() -> None:
    b = fresh("A")
    with pytest.raises(ValidationFailed) as exc:
        b.correct(1, "outcome", {"ending": "winner", "winning_side": "A"})
    assert codes(exc) == [("value", "unchanged")]


def test_a_scored_rally_becomes_a_replay_and_back_in_one_change_each() -> None:
    b = fresh("A", "A", "B")
    b.correct(2, "outcome", {"ending": "replay"})
    rows = b.sheet()["rows"]
    assert (rows[1]["ending"], rows[1]["winning_side"], rows[1]["corrected_by_user"]) == (
        "replay",
        None,
        True,
    )
    assert rows[1]["score_after"] == rows[1]["score_before"]  # a replay scores nothing
    b.correct(2, "outcome", {"ending": "fault", "winning_side": "B", "fault_kind": "nvz"})
    row = b.sheet()["rows"][1]
    assert (row["ending"], row["winning_side"], row["fault_kind"]) == ("fault", "B", "nvz")
    assert [c.kind for c in b.b.changes[-2:]] == ["correction", "correction"]


def test_a_side_swap_with_a_responsible_player_is_one_change() -> None:
    b = Book().start()
    b.tag("A", ending="winner")
    b.correct(1, "responsible_player", "A1")  # winner by A1
    b.correct(1, "outcome", {"ending": "winner", "winning_side": "B", "responsible_player": "B2"})
    row = b.sheet()["rows"][0]
    assert (row["winning_side"], row["responsible_player"]) == ("B", "B2")


def test_the_whole_outcome_change_is_audited_once_and_undone_byte_for_byte() -> None:
    b = fresh("A", "B")
    before = b.bytes()
    changes = len(b.b.changes)
    b.correct(1, "outcome", {"ending": "replay"})
    assert len(b.b.changes) == changes + 1
    change = b.b.changes[-1]
    assert (change.kind, change.field, change.old_value, change.new_value) == (
        "correction",
        "outcome",
        WIN_A,
        REPLAY,
    )
    b.undo()
    assert b.bytes() == before
