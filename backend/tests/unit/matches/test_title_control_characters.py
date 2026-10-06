"""C-01 (SEC-R6-S1-01, blocker): a control or surrogate character in a match title, or in a
nickname, is a field error (``title_invalid`` / ``nickname_invalid``), never a 500.

sprint-02 §5 TDD order: 1. NUL and every Cc/Cs character refused; 2. a Hypothesis test over
arbitrary text never raises anything but ``InvalidSetup`` (testing-strategy rule L11).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.matches.domain import (
    InvalidId,
    InvalidMatch,
    InvalidSetup,
    Match,
    MatchId,
    MatchSetup,
    OwnerId,
)

TODAY = dt.date(2026, 10, 5)
CONTROL = [chr(c) for c in range(0x20)] + [chr(0x7F)] + [chr(c) for c in range(0x80, 0xA0)]
SURROGATES = ["\ud800", "\udfff"]
SEPARATORS = [" ", " "]
BAD = CONTROL + SURROGATES + SEPARATORS


def codes(body: dict[str, Any]) -> list[tuple[str | None, str]]:
    with pytest.raises(InvalidSetup) as exc:
        MatchSetup.parse(body, today=TODAY)
    return [(f.field, f.code) for f in exc.value.fields]


@pytest.mark.parametrize("ch", BAD, ids=lambda c: f"U+{ord(c):04X}")
def test_a_title_with_a_control_or_surrogate_character_is_title_invalid(ch: str) -> None:
    assert codes({"format": "singles", "title": f"Sat{ch}urday"}) == [("title", "title_invalid")]


@pytest.mark.parametrize("ch", SURROGATES + SEPARATORS + ["\x00"], ids=lambda c: f"U+{ord(c):04X}")
def test_a_nickname_with_a_surrogate_or_separator_is_nickname_invalid(ch: str) -> None:
    people = [
        {"slot": "A1", "nickname": f"I{ch}vy", "is_me": True},
        {"slot": "B1", "nickname": "Carlos", "is_me": False},
    ]
    assert codes({"format": "singles", "participants": people}) == [
        ("participants.A1.nickname", "nickname_invalid")
    ]


def test_match_create_refuses_a_nul_title_too() -> None:
    with pytest.raises(InvalidMatch):
        Match.create(owner_id=OwnerId(MatchId.new().value), title="a\x00b", format="singles")


def test_a_tab_free_unicode_title_is_kept() -> None:
    parsed = MatchSetup.parse({"format": "singles", "title": "Sábado · 双打"}, today=TODAY)
    assert parsed.title == "Sábado · 双打"


@pytest.mark.parametrize("raw", ["\x00", "\ud800", "0000\x00-0000"])
def test_a_match_id_with_a_bad_character_is_invalid_id(raw: str) -> None:
    with pytest.raises(InvalidId):
        MatchId(raw)


@given(st.text(alphabet=st.characters(codec=None), max_size=40))
def test_any_title_or_nickname_gives_a_setup_or_invalid_setup(text: str) -> None:
    body = {
        "format": "singles",
        "title": text,
        "participants": [
            {"slot": "A1", "nickname": text, "is_me": True},
            {"slot": "B1", "nickname": "Carlos", "is_me": False},
        ],
    }
    try:
        parsed = MatchSetup.parse(body, today=TODAY)
    except InvalidSetup:
        return
    parsed.title.encode("utf-8")
    assert "\x00" not in parsed.title
    for member in parsed.participants.members if parsed.participants else ():
        member.nickname.encode("utf-8")
