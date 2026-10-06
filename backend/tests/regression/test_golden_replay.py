"""Golden replay of every stored fixture match (G02-07; NFR-075, QD-TR-04; ST-039 QA).

Each fixture match is driven through the scorebook commands (``Scorebook.start_game``, ``tag``,
``correct``) with fixed ids and clock, projected, and its canonical bytes must equal the stored
golden file under ``golden/`` byte for byte. The golden files were written once with
``RA_WRITE_GOLDEN=1`` and reviewed; a missing file fails, it is never created silently.

Fixtures (sprint-02 scorecard §4 G02-07): the 6-rally journey v1, IT-02-01's 30 rallies, and the
conflict game (A 11-0 at rally 14, rally 11 corrected, rallies 12-14 kept as needs_decision;
C-02, @needs-verification). The rows are also checked against the independent stepper
``scripts/measure/taglib.py`` so a golden file cannot have been written from a wrong engine.
"""

from __future__ import annotations

import itertools
import os
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tests.support import contract
from tests.support.scorebook import taglib

pytestmark = [pytest.mark.golden_replay, pytest.mark.scoring]

GOLDEN = Path(__file__).with_name("golden")
WINNERS_30 = "BABBBABABABABBABAAAAAABABBBBBB"  # IT-02-01 (10-7-1 after rally 30)
ROW_FIELDS = (
    "number", "serving_side", "score_before", "score_after", "winning_side", "ending", "marker",
)  # fmt: skip


class Fixture:
    """A scorebook driven through its commands with deterministic ids, clock and versions."""

    def __init__(self) -> None:
        ids = (uuid.UUID(int=i) for i in itertools.count(1))
        self.ctx = contract.SCOREBOOK_CONTEXT.load()(
            actor_id=uuid.UUID(int=0),
            at=datetime(2026, 11, 2, tzinfo=UTC),
            new_id=lambda: next(ids),
        )
        self.book = contract.SCOREBOOK.load().new(
            rules_version=contract.PROVISIONAL_PRESET, format="doubles", best_of=3
        )
        self.rally_ids: list[uuid.UUID] = []

    def start(self, side: str) -> Fixture:
        self.book = self.book.start_game(
            first_serving_side=contract.RULES_SIDE.load()[side], ends_switched=False,
            ready=True, expected_version=self.book.version, ctx=self.ctx,
        )  # fmt: skip
        return self

    def tag(self, tags: list[dict[str, Any]]) -> Fixture:
        times, outcome = contract.RALLY_TIMES.load(), contract.OUTCOME_INPUT.load()
        for t in tags:
            body = {k: t[k] for k in ("winning_side", "ending", "responsible_player", "fault_kind")}
            self.book, rally = self.book.tag(
                times.parse(t["start_ms"], t["end_ms"]),
                outcome.parse(body, format="doubles"),
                ready=True, expected_version=self.book.version, ctx=self.ctx,
            )  # fmt: skip
            self.rally_ids.append(rally.id)
        return self

    def correct_winner(self, number: int, side: str) -> Fixture:
        self.book = self.book.correct(
            self.rally_ids[number - 1], "winning_side", side,
            expected_version=self.book.version, ctx=self.ctx,
        )  # fmt: skip
        return self

    def sheet(self) -> dict[str, Any]:
        sheet: dict[str, Any] = contract.PROJECT.load()(self.book)
        return sheet

    def canonical(self) -> bytes:
        data: bytes = contract.CANONICAL_BYTES.load()(self.sheet())
        return data


def _winners(winners: str) -> list[dict[str, Any]]:
    plain = {"ending": "winner", "responsible_player": None, "fault_kind": None}
    tags: list[dict[str, Any]] = taglib.with_times(
        [{"winning_side": w, **plain} for w in winners], duration_ms=60_000
    )
    return tags


def journey_v1() -> tuple[Fixture, list[dict[str, Any]]]:
    tags = taglib.JOURNEY_TAGS
    return Fixture().start("A").tag(tags), tags


def it_02_01_thirty() -> tuple[Fixture, list[dict[str, Any]]]:
    tags = _winners(WINNERS_30)
    return Fixture().start("A").tag(tags), tags


def conflict_needs_decision() -> tuple[Fixture, list[dict[str, Any]]]:
    fixture = Fixture().start("A").tag(taglib.CONFLICT_TAGS).correct_winner(11, "A")
    return fixture, taglib.with_winner(taglib.CONFLICT_TAGS, rally=11, side="A")


FIXTURES: dict[str, Callable[[], tuple[Fixture, list[dict[str, Any]]]]] = {
    "journey_v1": journey_v1,
    "it_02_01_thirty": it_02_01_thirty,
    "conflict_needs_decision": conflict_needs_decision,
}


def _rows(sheet: dict[str, Any]) -> list[dict[str, Any]]:
    return [{f: row.get(f) for f in ROW_FIELDS} for row in sheet["rows"]]


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_golden_replay_is_byte_identical(name: str) -> None:
    fixture, tags = FIXTURES[name]()
    path = GOLDEN / f"{name}.json"
    data = fixture.canonical()
    if os.environ.get("RA_WRITE_GOLDEN") == "1":
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data + b"\n")
    assert path.exists(), f"no golden file {path.name}: write it with RA_WRITE_GOLDEN=1, review it"

    # the stored rules version is the one the golden file was made under (NFR-075)
    assert {g["rules_version"] for g in fixture.sheet()["games"]} == {contract.PROVISIONAL_PRESET}
    # independent rows (taglib stepper), so the golden file is not the engine checking itself
    reference = taglib.expected_rows(tags, first_serving_side="A")
    expected = [{f: r.get(f) for f in ROW_FIELDS} for r in reference]
    assert _rows(fixture.sheet()) == expected
    # replay: the same inputs project to the same bytes, now and as stored
    assert data == fixture.canonical()
    assert data == path.read_bytes().rstrip(b"\n")


def test_golden_replay_detects_a_changed_input() -> None:
    """Mutant check: one rally's winner flipped no longer matches the stored bytes."""
    fixture = Fixture().start("A").tag(_winners(WINNERS_30[:4] + "A" + WINNERS_30[5:]))
    assert fixture.canonical() != (GOLDEN / "it_02_01_thirty.json").read_bytes().rstrip(b"\n")
