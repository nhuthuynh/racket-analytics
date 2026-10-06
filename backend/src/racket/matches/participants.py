"""Match setup values: ``Participants`` and the parsed ``POST /matches`` body (ST-016).

Pure Python, part of the Match & Scoring domain (re-exported by ``racket.matches.domain``;
ADR 0024; api-sprint-01 §5). Every failure is a ``FieldError`` with a path and a code from the
closed table (api-sprint-01 §4.2); no input value is ever kept in an error. All failures are
reported together, in the form order of api-sprint-01 §5.3. The clock is an input (``today``).
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from racket.platform.errors import FieldError, ValidationFailed
from racket.platform.text import is_plain_line

NICKNAME_MAX = 30
TITLE_MAX = 120
EARLIEST_PLAYED_ON = dt.date(2000, 1, 1)
SLOTS = {"doubles": ("A1", "A2", "B1", "B2"), "singles": ("A1", "B1")}
ALL_SLOTS = ("A1", "A2", "B1", "B2")
SIDE_CODES = {"doubles": "side_needs_two_players", "singles": "side_needs_one_player"}
SCORING_SYSTEMS = ("side_out",)
UNAVAILABLE_SCORING_SYSTEMS = ("rally",)  # FR-043: shown, not selectable until verified
SETUP_KEYS = ("format", "scoring_system", "played_on", "title", "participants")
ENTRY_KEYS = {"slot", "nickname", "is_me"}
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_NOISE = re.compile(r"[\s\-.()]")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class InvalidSetup(ValidationFailed):
    """The match setup is not valid; ``fields`` lists every problem in form order."""


class InvalidParticipants(InvalidSetup):
    pass


@dataclass(frozen=True)
class MatchParticipant:
    slot: str
    nickname: str
    is_me: bool

    @property
    def side(self) -> str:
        return self.slot[0]


def _clean_nickname(raw: str) -> str:
    return unicodedata.normalize("NFC", raw).strip()


@dataclass(frozen=True)
class Participants:
    """The full set of players of one match, in slot order (ADR 0024). No IDs of their own."""

    format: str
    members: tuple[MatchParticipant, ...]

    @property
    def me(self) -> MatchParticipant:
        return next(m for m in self.members if m.is_me)

    @staticmethod
    def looks_like_contact_details(nickname: str) -> bool:
        """api-sprint-01 §5.4 (shared with the client): an email address, or 7+ digits once
        spaces, ``-``, ``.``, ``(``, ``)`` and a leading ``+`` are removed (judgment)."""
        text = nickname.strip()
        if _EMAIL.match(text):
            return True
        digits = _PHONE_NOISE.sub("", text)
        digits = digits.removeprefix("+")
        return len(digits) >= 7 and digits.isdigit()

    @classmethod
    def create(cls, format: str, entries: Any) -> Participants:
        problems = list(cls.problems(format, entries))
        if problems:
            raise InvalidParticipants("participants are not valid", problems)
        members = sorted(
            (
                MatchParticipant(e["slot"], _clean_nickname(e["nickname"]), e["is_me"])
                for e in entries
            ),
            key=lambda m: ALL_SLOTS.index(m.slot),
        )
        return cls(format=format, members=tuple(members))

    @classmethod
    def problems(cls, format: str, entries: Any) -> Iterable[FieldError]:
        """Every rule of ADR 0024, in the order of api-sprint-01 §5.3."""
        if not isinstance(entries, list) or not all(_is_entry(e) for e in entries):
            yield FieldError("participants", "invalid")
            return
        slots = [e["slot"] for e in entries]
        if any(s not in ALL_SLOTS for s in slots) or len(set(slots)) != len(slots):
            yield FieldError("participants", "invalid_slot")
        wanted = SLOTS[format]
        for side in ("A", "B"):
            expected = {s for s in wanted if s[0] == side}
            given = {s for s in slots if s in ALL_SLOTS and s[0] == side}
            count = sum(1 for s in slots if s in ALL_SLOTS and s[0] == side)
            if given != expected or count != len(expected):
                yield FieldError(f"participants.side_{side.lower()}", SIDE_CODES[format])
        for entry in sorted(
            (e for e in entries if e["slot"] in ALL_SLOTS), key=lambda e: ALL_SLOTS.index(e["slot"])
        ):
            code = _nickname_problem(entry["nickname"])
            if code:
                yield FieldError(f"participants.{entry['slot']}.nickname", code)
        if sum(1 for e in entries if e["is_me"]) != 1:
            yield FieldError("participants.me", "choose_one_me")


def _is_entry(entry: Any) -> bool:
    return (
        isinstance(entry, Mapping)
        and set(entry) == ENTRY_KEYS
        and isinstance(entry["slot"], str)
        and isinstance(entry["nickname"], str)
        and isinstance(entry["is_me"], bool)
    )


def _nickname_problem(raw: str) -> str | None:
    nickname = _clean_nickname(raw)
    if not nickname:
        return "nickname_required"
    if not is_plain_line(nickname):  # Cc, and Cs/Zl/Zp too (C-01)
        return "nickname_invalid"
    if len(nickname) > NICKNAME_MAX:
        return "nickname_too_long"
    return None


def default_title(format: str, played_on: dt.date) -> str:
    """flows D-2: "{Doubles|Singles} · {d Mon yyyy}"."""
    return f"{format.capitalize()} · {played_on.day} {_MONTHS[played_on.month - 1]} " + str(
        played_on.year
    )


@dataclass(frozen=True)
class MatchSetup:
    """The validated ``POST /matches`` body (api-sprint-01 §5.1). ``rules_version`` is never
    an input: the server sets it (T-MS-1)."""

    format: str
    scoring_system: str
    played_on: dt.date
    title: str
    participants: Participants | None

    @classmethod
    def parse(cls, body: Any, *, today: dt.date) -> MatchSetup:
        if not isinstance(body, Mapping):
            raise InvalidSetup("body is not an object", [FieldError(None, "invalid")])
        problems: list[FieldError] = []
        if any(key not in SETUP_KEYS for key in body):
            problems.append(FieldError(None, "unknown_field"))  # never the key itself (T-MS-3)

        raw_format = body.get("format")
        match_format: str | None = None
        if raw_format is None:
            problems.append(FieldError("format", "format_required"))
        elif isinstance(raw_format, str) and raw_format in SLOTS:  # never hash JSON (IT-02-10)
            match_format = raw_format
        else:
            problems.append(FieldError("format", "format_invalid"))

        system = body.get("scoring_system", "side_out")
        if system in UNAVAILABLE_SCORING_SYSTEMS:
            problems.append(FieldError("scoring_system", "scoring_system_unavailable"))
        elif system not in SCORING_SYSTEMS:
            problems.append(FieldError("scoring_system", "scoring_system_invalid"))

        played_on = today
        if "played_on" in body:
            parsed = _parse_date(body["played_on"])
            if parsed is None or parsed < EARLIEST_PLAYED_ON:
                problems.append(FieldError("played_on", "played_on_invalid"))
            elif parsed > today + dt.timedelta(days=1):  # a user east of UTC (api §5.1)
                problems.append(FieldError("played_on", "played_on_in_future"))
            else:
                played_on = parsed

        title: str | None = None
        if "title" in body:
            raw_title = body["title"]
            title = raw_title.strip() if isinstance(raw_title, str) else ""
            if not 1 <= len(title) <= TITLE_MAX or not is_plain_line(title):  # C-01
                problems.append(FieldError("title", "title_invalid"))

        participants: Participants | None = None
        if "participants" in body:
            if match_format is None:
                problems.append(FieldError("participants", "participants_without_format"))
            else:
                found = list(Participants.problems(match_format, body["participants"]))
                problems += found
                if not found:
                    participants = Participants.create(match_format, body["participants"])

        if problems or match_format is None:
            raise InvalidSetup("match setup is not valid", problems)
        return cls(
            format=match_format,
            scoring_system=str(system),
            played_on=played_on,
            title=title or default_title(match_format, played_on),
            participants=participants,
        )


def _parse_date(raw: Any) -> dt.date | None:
    if not isinstance(raw, str) or not _DATE.fullmatch(raw):
        return None
    try:
        return dt.date.fromisoformat(raw)
    except ValueError:
        return None
