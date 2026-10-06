"""Scorebook application service (ST-027, ST-030; match-aggregate §4).

Each command: lock the match row, load the scorebook, run the pure command (version check
first), save the difference, commit, and answer the new projection. Nothing is written when
any step fails (IT-02-02). Logs carry ``match_id`` and the pseudonymous account id only
(IT-02-09; the request's ``user_id`` log field).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from racket.matches.domain import Match, MatchStatus
from racket.matches.scorebook.domain import (
    CommandContext,
    InvalidRally,
    OutcomeInput,
    RallyNotFound,
    RallyTimes,
    Scorebook,
    StaleMatch,
    project,
)
from racket.matches.scorebook.repository import ScorebookRepository
from racket.platform.errors import FieldError, ValidationFailed
from racket.sports.pickleball.rules import Side
from racket.video_ingest.public import media_summary

log = logging.getLogger(__name__)
TAG_KEYS = frozenset(
    {"start_ms", "end_ms", "ending", "winning_side", "responsible_player", "fault_kind"}
)
START_KEYS = frozenset({"first_serving_side", "ends_switched"})


def parse_version(raw: str | None) -> int:
    """``If-Match`` as the client sends it: ``3``, ``"3"`` or ``W/"3"`` (BE-D1-02). Missing or
    malformed is a stale version: the client must reload before it changes anything."""
    value = (raw or "").strip().removeprefix("W/").strip('"')
    if not value.isascii() or not value.isdigit() or len(value) > 9:
        raise StaleMatch("If-Match missing or malformed")
    return int(value)


def _object(body: Any, keys: frozenset[str], error: type[ValidationFailed]) -> Mapping[str, Any]:
    if not isinstance(body, Mapping):
        raise error("body is not an object", [FieldError(None, "invalid")])
    if any(key not in keys for key in body):
        raise error("unknown field", [FieldError(None, "unknown_field")])
    return body


class ScorebookService:
    def __init__(self, session: Session, clock: Callable[[], datetime] | None = None) -> None:
        self.session = session
        self.books = ScorebookRepository(session)
        self.clock = clock or (lambda: datetime.now(UTC))

    def _video_ms(self, match: Match) -> int | None:
        """The probed duration of the match video, or ``None`` when it is not known yet
        (QA-S2-API-02: a rally lies inside the video, FR-027). Read through Capture & Media's
        published port (context map rule 1)."""
        facts = media_summary(self.session, match.id.value).facts
        return None if facts is None else facts.duration_ms

    def sheet(self, match: Match) -> tuple[int, dict[str, Any]]:
        book = self.books.load(match.id.value)
        return book.version, project(book)

    def _run(
        self, match: Match, actor_id: uuid.UUID, command: Callable[..., Any], event: str
    ) -> tuple[Scorebook, Any]:
        before = self.books.load(match.id.value, lock=True)
        ctx = CommandContext(actor_id=actor_id, at=self.clock())
        try:
            result = command(before, ctx, match.status is MatchStatus.VIDEO_RECEIVED)
        except Exception:
            self.session.rollback()
            raise
        after, extra = result if isinstance(result, tuple) else (result, None)
        self.books.save(match.id.value, before, after)
        self.session.commit()
        log.info(
            "scorebook changed",
            extra={"event": event, "match_id": str(match.id), "version": after.version},
        )
        return after, extra

    def start_game(self, match: Match, actor_id: uuid.UUID, body: Any, version: int) -> Scorebook:
        start = _object(body, START_KEYS, ValidationFailed)
        side, ends = start.get("first_serving_side"), start.get("ends_switched", False)
        problems = []
        if side not in ("A", "B"):
            problems.append(FieldError("first_serving_side", "side_invalid"))
        if not isinstance(ends, bool):
            problems.append(FieldError("ends_switched", "invalid"))
        if problems:
            raise ValidationFailed("game start is not valid", problems)

        def command(book: Scorebook, ctx: CommandContext, ready: bool) -> Scorebook:
            return book.start_game(
                first_serving_side=Side(side),
                ends_switched=ends,
                ready=ready,
                expected_version=version,
                ctx=ctx,
            )

        book, _ = self._run(match, actor_id, command, "match.game_started")
        return book

    def tag(
        self, match: Match, actor_id: uuid.UUID, body: Any, version: int
    ) -> tuple[Scorebook, uuid.UUID]:
        tag = _object(body, TAG_KEYS, InvalidRally)
        times = RallyTimes.parse(tag.get("start_ms"), tag.get("end_ms"))
        fields = {k: v for k, v in tag.items() if k not in ("start_ms", "end_ms")}
        outcome = OutcomeInput.parse(fields, format=match.format.value)
        video_ms = self._video_ms(match)

        def command(book: Scorebook, ctx: CommandContext, ready: bool) -> tuple[Scorebook, Any]:
            return book.tag(
                times, outcome, ready=ready, expected_version=version, ctx=ctx, video_ms=video_ms
            )

        book, rally = self._run(match, actor_id, command, "match.rally_tagged")
        return book, rally.id

    def correct(
        self, match: Match, actor_id: uuid.UUID, raw_rally_id: str, body: Any, version: int
    ) -> Scorebook:
        """FR-052/FR-053: ``{"field", "value"}``; ``{"field": "withdrawn", "value": true}``
        withdraws the rally (it stays stored and audited)."""
        change = _object(body, CORRECTION_KEYS, ValidationFailed)
        if set(change) != CORRECTION_KEYS:
            raise ValidationFailed("field and value are required", [FieldError(None, "invalid")])
        rally_id = _rally_id(raw_rally_id)
        video_ms = self._video_ms(match) if change["field"] in ("start_ms", "end_ms") else None

        def command(book: Scorebook, ctx: CommandContext, ready: bool) -> Scorebook:
            return book.correct(
                rally_id,
                change["field"],
                change["value"],
                expected_version=version,
                ctx=ctx,
                video_ms=video_ms,
            )

        book, _ = self._run(match, actor_id, command, "match.rally_corrected")
        return book

    def undo(self, match: Match, actor_id: uuid.UUID, version: int) -> Scorebook:
        def command(book: Scorebook, ctx: CommandContext, ready: bool) -> Scorebook:
            return book.undo(expected_version=version, ctx=ctx)

        book, _ = self._run(match, actor_id, command, "match.undone")
        return book

    def resolve(
        self, match: Match, actor_id: uuid.UUID, raw_rally_id: str, body: Any, version: int
    ) -> Scorebook:
        """FR-053 (a), provisional: ``{"decision": "withdraw" | "move_to_next_game"}``."""
        decision = _object(body, frozenset({"decision"}), ValidationFailed).get("decision")
        rally_id = _rally_id(raw_rally_id)

        def command(book: Scorebook, ctx: CommandContext, ready: bool) -> Scorebook:
            return book.resolve(rally_id, decision, expected_version=version, ctx=ctx)

        book, _ = self._run(match, actor_id, command, "match.rally_resolved")
        return book

    def rally_start(self, match: Match, raw_rally_id: str) -> int:
        """The start of a kept rally of this match, in ms from the video start (FR-027)."""
        rally_id = _rally_id(raw_rally_id)
        book = self.books.load(match.id.value)
        rally = next((r for r in book.kept if r.id == rally_id), None)
        if rally is None:
            raise RallyNotFound("no such rally in this match")
        return rally.times.start_ms

    def history(self, match: Match) -> list[dict[str, Any]]:
        """FR-052: every change, oldest first, with the rally's current sheet number. Values
        are tag values only (sides, slots, enums, integers): no names, no free text."""
        book = self.books.load(match.id.value)
        numbers = {row["rally_id"]: row["number"] for row in project(book)["rows"]}
        return [
            {
                "id": str(c.id),
                "kind": c.kind,
                "rally_id": None if c.rally_id is None else str(c.rally_id),
                "rally_number": None if c.rally_id is None else numbers.get(str(c.rally_id)),
                "game": c.game_number,
                "field": c.field,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "undoes": None if c.undoes is None else str(c.undoes),
                "at": c.at.astimezone(UTC)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z"),
            }
            for c in book.changes
        ]


CORRECTION_KEYS = frozenset({"field", "value"})


def _rally_id(raw: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise RallyNotFound("not a rally id") from None
