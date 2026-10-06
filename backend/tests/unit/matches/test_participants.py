"""``Participants`` and the match-setup validation (ST-016; ADR 0024; api-sprint-01 §5.3, §5.4).

sprint-01 §5 TDD order: 1. doubles with 3 nicknames -> error naming the side; 2. two "me"
markers -> error; 3. a nickname that looks like an email address -> flagged, still accepted.
Then the remaining rules of ADR 0024 and the closed field-code table, all pure (no I/O, clock).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.matches.domain import (
    InvalidParticipants,
    InvalidSetup,
    MatchSetup,
    Participants,
)

TODAY = dt.date(2026, 10, 5)
NAMES = {"A1": "Ivy", "A2": "Dana", "B1": "Carlos", "B2": "Sam"}


def people(*slots: str, me: tuple[str, ...] = ("A1",)) -> list[dict[str, Any]]:
    return [{"slot": s, "nickname": NAMES[s], "is_me": s in me} for s in slots]


def codes(exc: pytest.ExceptionInfo[Any]) -> list[tuple[str | None, str]]:
    return [(f.field, f.code) for f in exc.value.fields]


# ---------------------------------------------------------------- 1. slot counts per side
def test_doubles_with_three_nicknames_names_the_short_side() -> None:
    with pytest.raises(InvalidParticipants) as exc:
        Participants.create("doubles", people("A1", "A2", "B1"))
    assert codes(exc) == [("participants.side_b", "side_needs_two_players")]


def test_singles_with_an_extra_player_names_that_side() -> None:
    with pytest.raises(InvalidParticipants) as exc:
        Participants.create("singles", people("A1", "B1", "A2"))
    assert codes(exc) == [("participants.side_a", "side_needs_one_player")]


def test_both_sides_wrong_are_both_reported_in_side_order() -> None:
    with pytest.raises(InvalidParticipants) as exc:
        Participants.create("doubles", people("A1", "B1"))
    assert codes(exc) == [
        ("participants.side_a", "side_needs_two_players"),
        ("participants.side_b", "side_needs_two_players"),
    ]


@pytest.mark.parametrize("slot", ["C1", "a1", "", "A3"])
def test_an_unknown_slot_is_invalid_slot(slot: str) -> None:
    entries = people("A1", "A2", "B1", "B2")
    entries.append({"slot": slot, "nickname": "X", "is_me": False})
    with pytest.raises(InvalidParticipants) as exc:
        Participants.create("doubles", entries)
    assert ("participants", "invalid_slot") in codes(exc)


def test_a_repeated_slot_is_invalid_slot() -> None:
    entries = people("A1", "A2", "B1", "B2")
    entries.append({"slot": "B2", "nickname": "Twin", "is_me": False})
    with pytest.raises(InvalidParticipants) as exc:
        Participants.create("doubles", entries)
    assert ("participants", "invalid_slot") in codes(exc)


# ---------------------------------------------------------------- 2. exactly one "me"
@pytest.mark.parametrize("me", [("A1", "B1"), (), ("A1", "A2", "B1", "B2")])
def test_zero_or_several_me_markers_are_refused(me: tuple[str, ...]) -> None:
    with pytest.raises(InvalidParticipants) as exc:
        Participants.create("doubles", people("A1", "A2", "B1", "B2", me=me))
    assert codes(exc) == [("participants.me", "choose_one_me")]


# ---------------------------------------------------------------- 3. contact-detail warning
@pytest.mark.parametrize(
    "nickname",
    ["carlos@example.com", " ivy@club.org ", "+61 (2) 9876-5432", "0412 345 678", "1234567"],
)
def test_contact_details_are_flagged(nickname: str) -> None:
    assert Participants.looks_like_contact_details(nickname) is True


@pytest.mark.parametrize("nickname", ["Carlos", "Ivy 2", "@ivy", "a@b", "123456", "Court 7 Sam"])
def test_ordinary_nicknames_are_not_flagged(nickname: str) -> None:
    assert Participants.looks_like_contact_details(nickname) is False


def test_a_contact_like_nickname_is_still_accepted() -> None:
    entries = people("A1", "B1")
    entries[1]["nickname"] = "carlos@example.com"
    participants = Participants.create("singles", entries)
    assert participants.members[1].nickname == "carlos@example.com"


# ---------------------------------------------------------------- nickname rules
@pytest.mark.parametrize(
    ("nickname", "code"),
    [
        ("", "nickname_required"),
        ("   ", "nickname_required"),
        ("x" * 31, "nickname_too_long"),
        ("Ivy\x00", "nickname_invalid"),
        ("Iv\ny", "nickname_invalid"),
    ],
)
def test_bad_nicknames_name_their_slot(nickname: str, code: str) -> None:
    entries = people("A1", "B1")
    entries[1]["nickname"] = nickname
    with pytest.raises(InvalidParticipants) as exc:
        Participants.create("singles", entries)
    assert codes(exc) == [("participants.B1.nickname", code)]


def test_nicknames_are_trimmed_and_nfc_normalised_and_30_characters_fit() -> None:
    entries = people("A1", "B1")
    entries[0]["nickname"] = "  Zoé  "  # e + combining acute -> one character
    entries[1]["nickname"] = "y" * 30
    participants = Participants.create("singles", entries)
    assert [m.nickname for m in participants.members] == ["Zoé", "y" * 30]


def test_duplicate_nicknames_are_allowed() -> None:
    entries = people("A1", "B1")
    entries[1]["nickname"] = "Ivy"
    assert len(Participants.create("singles", entries).members) == 2


# ---------------------------------------------------------------- shape and order
def test_members_are_kept_in_slot_order_and_compare_by_value() -> None:
    a = Participants.create("doubles", list(reversed(people("A1", "A2", "B1", "B2"))))
    b = Participants.create("doubles", people("A1", "A2", "B1", "B2"))
    assert [m.slot for m in a.members] == ["A1", "A2", "B1", "B2"]
    assert a == b
    assert a.me.slot == "A1"


def test_a_non_list_or_malformed_entry_is_invalid() -> None:
    with pytest.raises(InvalidParticipants) as exc:
        Participants.create("doubles", "Ivy, Dana")  # type: ignore[arg-type]
    assert codes(exc) == [("participants", "invalid")]
    with pytest.raises(InvalidParticipants) as exc:
        Participants.create("singles", [{"slot": "A1"}, *people("B1")])
    assert ("participants", "invalid") in codes(exc)


# ---------------------------------------------------------------- MatchSetup (POST /matches body)
def setup(**body: Any) -> MatchSetup:
    return MatchSetup.parse(body, today=TODAY)


def setup_codes(**body: Any) -> list[tuple[str | None, str]]:
    with pytest.raises(InvalidSetup) as exc:
        setup(**body)
    return codes(exc)


def test_missing_format_is_required_and_participants_need_a_format() -> None:
    assert setup_codes(participants=people("A1", "B1")) == [
        ("format", "format_required"),
        ("participants", "participants_without_format"),
    ]


def test_unknown_format_is_invalid() -> None:
    assert setup_codes(format="triples") == [("format", "format_invalid")]


@pytest.mark.parametrize(
    ("system", "code"),
    [("rally", "scoring_system_unavailable"), ("bogus", "scoring_system_invalid"),
     (3, "scoring_system_invalid")],
)  # fmt: skip
def test_scoring_system_other_than_side_out_is_refused(system: Any, code: str) -> None:
    assert setup_codes(format="doubles", scoring_system=system) == [("scoring_system", code)]


@pytest.mark.parametrize(
    ("played_on", "code"),
    [
        ("2026-10-07", "played_on_in_future"),
        ("1999-12-31", "played_on_invalid"),
        ("2026-13-01", "played_on_invalid"),
        ("05/10/2026", "played_on_invalid"),
        (20261005, "played_on_invalid"),
    ],
)
def test_bad_dates_are_refused(played_on: Any, code: str) -> None:
    assert setup_codes(format="singles", played_on=played_on) == [("played_on", code)]


def test_today_plus_one_is_accepted_for_users_east_of_utc() -> None:
    assert setup(format="singles", played_on="2026-10-06").played_on == dt.date(2026, 10, 6)


@pytest.mark.parametrize("title", ["", "   ", "t" * 121, 7])
def test_bad_titles_are_refused(title: Any) -> None:
    assert setup_codes(format="singles", title=title) == [("title", "title_invalid")]


@pytest.mark.parametrize("key", ["rules_version", "owner_id", "status", "<script>"])
def test_unknown_keys_are_reported_without_their_name(key: str) -> None:
    assert setup_codes(format="singles", **{key: "x"}) == [(None, "unknown_field")]


def test_all_failures_come_together_in_form_order() -> None:
    assert [f for f, _ in setup_codes(
        format="doubles", scoring_system="rally", played_on="2099-01-01", title="",
        participants=people("A1", "A2", "B1", me=("A1", "A2")), extra=1,
    )] == [None, "scoring_system", "played_on", "title", "participants.side_b",
           "participants.me"]  # fmt: skip


def test_defaults_side_out_today_and_a_title_from_format_and_date() -> None:
    parsed = setup(format="doubles", played_on="2026-10-03")
    assert parsed.scoring_system == "side_out"
    assert parsed.title == "Doubles · 3 Oct 2026"
    assert parsed.participants is None
    assert setup(format="singles").played_on == TODAY
    assert setup(format="singles").title == "Singles · 5 Oct 2026"


def test_a_given_title_is_trimmed_and_kept() -> None:
    assert setup(format="singles", title="  Sat doubles  ").title == "Sat doubles"


@given(st.dictionaries(st.text(max_size=8), st.none() | st.integers() | st.text(max_size=12),
                       max_size=6))  # fmt: skip
def test_any_body_either_parses_or_gives_closed_codes_never_echoing_input(
    body: dict[str, Any],
) -> None:
    """Parser of untrusted input: property test (retro 0 L4)."""
    try:
        MatchSetup.parse(body, today=TODAY)
    except InvalidSetup as exc:
        for f in exc.fields:
            assert f.code in CLOSED_CODES
            assert f.field is None or f.field in KNOWN_FIELDS or f.field.startswith("participants")


CLOSED_CODES = {
    "email_invalid", "format_required", "format_invalid", "scoring_system_invalid",
    "scoring_system_unavailable", "played_on_invalid", "played_on_in_future", "title_invalid",
    "side_needs_two_players", "side_needs_one_player", "invalid_slot", "choose_one_me",
    "nickname_required", "nickname_too_long", "nickname_invalid", "participants_without_format",
    "unknown_field", "invalid",
}  # fmt: skip
KNOWN_FIELDS = {"format", "scoring_system", "played_on", "title", "participants"}


# ---------------------------------------------------------------- Match.set_up
def test_a_match_set_up_keeps_the_answers_and_the_server_preset() -> None:
    from racket.matches.domain import Match, OwnerId

    answers = setup(format="doubles", played_on="2026-10-03",
                    participants=people("A1", "A2", "B1", "B2", me=("B2",)))  # fmt: skip
    match = Match.set_up(owner_id=OwnerId.new(), setup=answers)
    assert (match.format, match.title, match.played_on) == (
        "doubles",
        "Doubles · 3 Oct 2026",
        dt.date(2026, 10, 3),
    )
    assert match.rules_version == "PROVISIONAL-UNVERIFIED"
    assert match.participants is not None
    assert match.participants.me.slot == "B2"
