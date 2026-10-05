"""The score sheet is a pure projection of the stored inputs (ST-026; FR-049; NFR-075;
match-aggregate §5).

sprint-02 §5 TDD order: 1. an empty match -> an empty sheet; 2. the projection equals
``fold`` over the outcomes (P6, property test); 3. replay rows show no score change (P8);
4. a golden replay is byte-identical (NFR-075, QD-TR-04). The preset is
PROVISIONAL-UNVERIFIED, so every sheet is "unofficial" (FR-055, ADR 0009, ADR 0023).
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from racket.matches.scorebook.domain import (
    UNOFFICIAL_LABEL,
    GameStart,
    OutcomeInput,
    Rally,
    RallyTimes,
    Scorebook,
    canonical_bytes,
    project,
)
from racket.sports.pickleball.rules import PRESETS, Side, fold, new_game

pytestmark = [pytest.mark.unit, pytest.mark.scoring]

CONFIG = PRESETS["PROVISIONAL-UNVERIFIED"]
GOLDEN = Path(__file__).with_name("golden") / "scorebook_journey_v1.json"


def book_with(winners: list[str | None], first: str = "A") -> Scorebook:
    """A stored scorebook built from values, independent of the command code (ST-027)."""
    rallies = tuple(
        Rally(
            id=uuid.UUID(int=i + 1),
            game_number=1,
            seq=i + 1,
            times=RallyTimes.parse(i * 1_000, i * 1_000 + 900),
            outcome=OutcomeInput.parse(
                {"ending": "replay" if side is None else "winner", "winning_side": side},
                format="doubles",
            ),
            created_version=i + 2,
        )
        for i, side in enumerate(winners)
    )
    game = GameStart(number=1, first_serving_side=Side(first), ends_switched=False,
                     created_version=1)  # fmt: skip
    return Scorebook(rules_version="PROVISIONAL-UNVERIFIED", format="doubles", best_of=3,
                     version=len(rallies) + 1, games=(game,), rallies=rallies)  # fmt: skip


def call(state) -> str:  # type: ignore[no-untyped-def]
    srv = state.serving_side
    return f"{state.score_of(srv)}-{state.score_of(srv.other)}-{state.server_number}"


# ---------------------------------------------------------------- 1. empty
def test_an_empty_match_has_an_empty_unofficial_sheet() -> None:
    sheet = project(Scorebook.new(rules_version="PROVISIONAL-UNVERIFIED", format="doubles",
                                  best_of=3))  # fmt: skip
    assert (sheet["rows"], sheet["games"], sheet["match_winner"]) == ([], [], None)
    assert sheet["rules_version"] == "PROVISIONAL-UNVERIFIED"
    assert (sheet["unofficial"], sheet["label"]) == (True, UNOFFICIAL_LABEL)


def test_the_label_is_the_fr_055_text() -> None:
    assert UNOFFICIAL_LABEL == "unofficial scoring (rules not yet verified)"


# ---------------------------------------------------------------- 2. projection = fold (P6)
@settings(max_examples=200)
@given(st.lists(st.sampled_from(["A", "B", None]), max_size=60), st.sampled_from(["A", "B"]))
def test_the_projection_equals_a_fold_over_the_outcomes(
    winners: list[str | None], first: str
) -> None:
    book = book_with(winners, first)
    sheet = project(book)
    state = new_game(CONFIG, Side(first))
    for row, side in zip(sheet["rows"], winners, strict=True):
        if state.is_over:
            assert (row["marker"], row["score_after"]) == ("needs_decision", None)
            continue
        ending = "replay" if side is None else "winner"
        body = {"ending": ending, "winning_side": side}
        outcome = OutcomeInput.parse(body, format="doubles").to_engine()
        after = fold([outcome], CONFIG, state)
        assert (row["score_before"], row["score_after"]) == (call(state), call(after))  # type: ignore[arg-type]
        assert row["serving_side"] == state.serving_side.value
        state = after  # type: ignore[assignment]
    assert sheet["games"][0]["winner"] == (state.winner.value if state.winner else None)


# ---------------------------------------------------------------- 3. replay (P8)
def test_a_replay_row_shows_no_score_change() -> None:
    sheet = project(book_with(["A", "A", None, "B"]))
    replay = sheet["rows"][2]
    assert (replay["ending"], replay["winning_side"]) == ("replay", None)
    assert replay["score_before"] == replay["score_after"] == "2-0-2"


# ---------------------------------------------------------------- 4. golden replay (NFR-075)
def test_the_sheet_has_no_floats_and_a_canonical_byte_form() -> None:
    sheet = project(book_with(["A", "B", "B", "A"]))
    raw = canonical_bytes(sheet)
    assert json.loads(raw) == sheet
    assert canonical_bytes(json.loads(raw)) == raw
    assert b" " not in raw.replace(b"unofficial scoring (rules not yet verified)", b"")


def test_a_golden_replay_is_byte_identical() -> None:
    book = book_with(["A", "B", "A", "A", None, "A", "B", "B", "A", "A"])
    assert canonical_bytes(project(book)) == GOLDEN.read_bytes().rstrip(b"\n")


def test_every_sheet_carries_the_rules_version_on_each_game() -> None:
    sheet = project(book_with(["A"]))
    assert sheet["games"][0]["rules_version"] == "PROVISIONAL-UNVERIFIED"
