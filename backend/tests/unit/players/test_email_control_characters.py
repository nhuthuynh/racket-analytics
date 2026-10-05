"""C-01 (SEC-R6-S1-01, blocker): control and surrogate characters in the address are refused.

sprint-02 §5 TDD order: 1. NUL and every Cc/Cs character refused (``None`` -> 422
``email_invalid`` at the API); 2. a Hypothesis test over arbitrary text never raises and never
returns an address Postgres or UTF-8 cannot store (testing-strategy rule L11).
"""

from __future__ import annotations

import sys
import unicodedata

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.players.domain import normalise_email

CONTROL = [chr(c) for c in range(0x20)] + [chr(0x7F)] + [chr(c) for c in range(0x80, 0xA0)]
SURROGATES = ["\ud800", "\udbff", "\udc00", "\udfff"]
SEPARATORS = [" ", " "]  # Zl/Zp: "line separator" (sprint-02 §14.3.1)


@pytest.mark.parametrize("ch", CONTROL + SURROGATES + SEPARATORS, ids=lambda c: f"U+{ord(c):04X}")
@pytest.mark.parametrize("where", ["local", "domain", "end"])
def test_a_control_or_surrogate_character_anywhere_is_refused(ch: str, where: str) -> None:
    raw = {
        "local": f"iv{ch}y@example.com",
        "domain": f"ivy@exa{ch}mple.com",
        "end": f"ivy@example.com{ch}x",
    }[where]
    assert normalise_email(raw) is None


def test_nul_alone_in_an_otherwise_valid_address_is_refused() -> None:
    assert normalise_email("ivy\x00@example.com") is None


def test_a_valid_address_is_still_accepted() -> None:
    assert normalise_email("  Ivy@Example.com ") == "ivy@example.com"


def _storable(text: str) -> bool:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return "\x00" not in text


@given(st.text(alphabet=st.characters(codec=None), max_size=80))
def test_any_text_never_raises_and_any_output_is_storable(raw: str) -> None:
    out = normalise_email(raw)
    if out is not None:
        assert _storable(out)
        assert not any(unicodedata.category(c) in {"Cc", "Cs", "Zl", "Zp"} for c in out)


@given(st.text(max_size=20), st.sampled_from(CONTROL + SURROGATES), st.text(max_size=20))
def test_an_inserted_bad_character_always_refuses(left: str, bad: str, right: str) -> None:
    assert normalise_email(f"{left}a{bad}b@example.com{right}") is None


assert sys.maxunicode > 0xFFFF  # the surrogates above are single code points
