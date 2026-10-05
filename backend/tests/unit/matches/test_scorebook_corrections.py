"""Corrections, withdrawals and undo (ST-031, ST-032 mechanics; FR-052, FR-053 (a)).

sprint-02 §5 TDD order, negative first. ``Correction``: 1. a non-existent rally -> error;
2. old and new values recorded; 3. corrections are only appended; 4. ``corrected_by_user``.
``Undo``: 1. nothing to undo -> error; 2. undoing a correction restores a byte-identical sheet
(C-04); 3. the undo is itself audited. ``replay_from(k)``: 1. a correction equals a fresh
build with the corrected outcomes (C-01); 2./3. rallies past a game's new end are kept and
marked ``needs_decision`` (C-02, C-03; provisional, ADR 0009).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from itertools import count
from typing import Any

import pytest

from racket.matches.scorebook.domain import (
    CommandContext,
    InvalidOutcome,
    InvalidRally,
    NothingToUndo,
    OutcomeInput,
    RallyNotFound,
    RallyTimes,
    Scorebook,
    StaleMatch,
    canonical_bytes,
    project,
)
from racket.platform.errors import ValidationFailed
from racket.sports.pickleball.rules import Side

pytestmark = [pytest.mark.unit, pytest.mark.scoring]

AT = datetime(2026, 10, 5, 12, tzinfo=UTC)


class Book:
    def __init__(self) -> None:
        ids = count(1)
        self.ctx = CommandContext(
            actor_id=uuid.UUID(int=99), at=AT, new_id=lambda: uuid.UUID(int=next(ids))
        )
        self.b = Scorebook.new(rules_version="PROVISIONAL-UNVERIFIED", format="doubles")
        self.ids: list[uuid.UUID] = []
        self.clock = 0

    @property
    def v(self) -> int:
        return self.b.version

    def start(self, first: str = "A") -> Book:
        self.b = self.b.start_game(
            first_serving_side=Side(first),
            ends_switched=False,
            ready=True,
            expected_version=self.v,
            ctx=self.ctx,
        )
        return self

    def tag(self, *sides: str | None, ending: str = "winner") -> Book:
        for side in sides:
            body = {"ending": "replay" if side is None else ending, "winning_side": side}
            times = RallyTimes.parse(self.clock, self.clock + 900)
            self.clock += 1_000
            self.b, rally = self.b.tag(
                times,
                OutcomeInput.parse(body, format="doubles"),
                ready=True,
                expected_version=self.v,
                ctx=self.ctx,
            )
            self.ids.append(rally.id)
        return self

    def correct(self, n: int, field: str, value: Any) -> Book:
        self.b = self.b.correct(
            self.ids[n - 1], field, value, expected_version=self.v, ctx=self.ctx
        )
        return self

    def undo(self) -> Book:
        self.b = self.b.undo(expected_version=self.v, ctx=self.ctx)
        return self

    def sheet(self) -> dict[str, Any]:
        return project(self.b)

    def bytes(self) -> bytes:
        return canonical_bytes(self.sheet())


def fresh(*sides: str | None) -> Book:
    return Book().start().tag(*sides)


# ---------------------------------------------------------------- Correction 1-4
def test_correcting_a_rally_that_does_not_exist_is_not_found() -> None:
    b = fresh("A")
    with pytest.raises(RallyNotFound) as exc:
        b.b.correct(uuid.uuid4(), "winning_side", "B", expected_version=b.v, ctx=b.ctx)
    assert exc.value.status == 404


@pytest.mark.parametrize(("field", "value"), [("score_after", "1-0-2"), ("seq", 3), ("", "A")])
def test_only_tag_fields_can_be_corrected(field: str, value: Any) -> None:
    b = fresh("A")
    with pytest.raises(ValidationFailed) as exc:
        b.correct(1, field, value)
    assert [(f.field, f.code) for f in exc.value.fields] == [("field", "field_invalid")]


def test_a_correction_with_a_stale_version_changes_nothing() -> None:
    b = fresh("A", "A")
    with pytest.raises(StaleMatch):
        b.b.correct(b.ids[0], "winning_side", "B", expected_version=b.v - 1, ctx=b.ctx)


def test_a_correction_that_breaks_the_outcome_rules_is_refused() -> None:
    b = Book().start().tag("A")
    b.b = b.b.correct(b.ids[0], "ending", "unforced_error", expected_version=b.v, ctx=b.ctx)
    b.correct(1, "responsible_player", "B1")
    with pytest.raises(InvalidOutcome):
        b.correct(1, "winning_side", "B")  # B1's error would now be on the winning side


def test_a_time_correction_may_not_overlap_another_rally() -> None:
    b = fresh("A", "A")
    with pytest.raises(InvalidRally):
        b.correct(2, "start_ms", 500)
    b.correct(2, "start_ms", 950)


def test_an_unchanged_value_is_not_a_correction() -> None:
    b = fresh("A")
    with pytest.raises(ValidationFailed) as exc:
        b.correct(1, "winning_side", "A")
    assert [(f.field, f.code) for f in exc.value.fields] == [("value", "unchanged")]


def test_a_correction_records_old_and_new_value_who_and_when() -> None:
    b = fresh("A", "B").correct(2, "winning_side", "A")
    change = b.b.changes[-1]
    assert (change.kind, change.rally_id, change.field) == ("correction", b.ids[1], "winning_side")
    assert (change.old_value, change.new_value) == ("B", "A")
    assert (change.actor_id, change.at, change.version) == (uuid.UUID(int=99), AT, b.v)


def test_corrections_are_only_appended() -> None:
    b = fresh("A", "B", "A")
    before = b.b.changes
    b.correct(2, "winning_side", "A").correct(3, "ending", "forced_error")
    assert b.b.changes[: len(before)] == before
    assert [c.kind for c in b.b.changes[len(before) :]] == ["correction", "correction"]


def test_a_correction_marks_only_that_rally_corrected_by_user() -> None:
    b = fresh("A", "B", "A").correct(2, "winning_side", "A")
    assert [r["corrected_by_user"] for r in b.sheet()["rows"]] == [False, True, False]


# ---------------------------------------------------------------- C-01 replay = fresh build
def test_c01_a_correction_rescores_later_rallies_like_a_fresh_build() -> None:
    sides: list[str | None] = ["A", "B", "B", "A", None, "A", "B", "A", "A", "B"] * 3
    b = fresh(*sides).correct(6, "winning_side", "B")
    rebuilt = fresh(*[*sides[:5], "B", *sides[6:]])
    got = [
        {k: r[k] for k in ("score_before", "score_after", "serving_side", "marker")}
        for r in b.sheet()["rows"]
    ]
    want = [
        {k: r[k] for k in ("score_before", "score_after", "serving_side", "marker")}
        for r in rebuilt.sheet()["rows"]
    ]
    assert got == want


# ---------------------------------------------------------------- Undo 1-3, C-04
def test_undo_with_nothing_to_undo_is_refused() -> None:
    with pytest.raises(NothingToUndo) as exc:
        Book().undo()
    assert (exc.value.status, exc.value.code) == (409, "nothing_to_undo")


def test_c04_undo_of_a_correction_restores_a_byte_identical_sheet() -> None:
    b = fresh(*(["A", "B", "B", "A", "A", "B"] * 5))
    before = b.bytes()
    b.correct(5, "winning_side", "B")
    assert b.bytes() != before
    b.undo()
    assert b.bytes() == before


def test_an_undo_is_itself_audited_and_points_at_what_it_undid() -> None:
    b = fresh("A", "B").correct(2, "winning_side", "A").undo()
    correction, undo = b.b.changes[-2:]
    assert (undo.kind, undo.undoes, undo.rally_id, undo.field) == (
        "undo",
        correction.id,
        b.ids[1],
        "winning_side",
    )
    assert (undo.old_value, undo.new_value) == ("A", "B")


def test_undo_of_a_tag_withdraws_the_rally_but_keeps_it_stored() -> None:
    b = fresh("A", "B")
    b.undo()
    assert len(b.b.rallies) == 2
    assert [r.withdrawn for r in b.b.rallies] == [False, True]
    assert b.b.changes[-1].kind == "undo"
    rows = b.sheet()["rows"]
    assert [r["rally_id"] for r in rows] == [str(b.ids[0])]


def test_undo_walks_back_change_by_change() -> None:
    b = fresh("A", "B", "A")
    states = [b.bytes()]
    b.correct(1, "winning_side", "B")
    states.append(b.bytes())
    b.correct(3, "ending", "forced_error")
    b.undo()
    assert b.bytes() == states[1]
    b.undo()
    assert b.bytes() == states[0]


def test_undo_of_a_game_start_removes_the_game() -> None:
    b = Book().start()
    b.undo()
    assert b.b.games == ()
    assert b.sheet()["games"] == []


def test_a_withdrawal_hides_the_rally_and_undo_brings_it_back() -> None:
    b = fresh("A", "B", "A")
    before = b.bytes()
    b.correct(2, "withdrawn", True)
    assert len(b.sheet()["rows"]) == 2
    assert b.b.changes[-1].kind == "withdrawal"
    b.undo()
    assert b.bytes() == before


# ---------------------------------------------------------------- C-02 / C-03 (provisional)
@pytest.mark.needs_verification
def test_c02_a_correction_that_ends_the_game_earlier_keeps_later_rallies_marked() -> None:
    sides = ["A"] * 10 + ["B", "A", "A", "A"]  # won 11-0 at rally 14 (taglib.CONFLICT_TAGS)
    b = fresh(*sides)
    assert b.sheet()["games"][0]["winner"] == "A"
    b.correct(11, "winning_side", "A")
    rows = b.sheet()["rows"]
    assert len(rows) == 14
    assert [r["number"] for r in rows if r["marker"] == "needs_decision"] == [12, 13, 14]
    assert rows[10]["score_after"] == "11-0-2"


@pytest.mark.needs_verification
def test_c03_a_correction_that_unends_a_game_marks_the_next_games_rallies() -> None:
    b = fresh(*(["A"] * 11))
    b.start("B").tag("B", "B", "A")
    b.correct(11, "winning_side", "B")
    sheet = b.sheet()
    assert sheet["games"][0]["winner"] is None
    assert [r["marker"] for r in sheet["rows"][11:]] == ["needs_decision"] * 3
    assert len(sheet["rows"]) == 14
