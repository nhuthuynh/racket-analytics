"""Analytics' published port: the purge job (deletion-and-purge.md §4.2, §5) and the read
model Coaching translates at its ACL (ST-055; coaching-plan.md §4, context map R8)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from racket.analytics.repository import SnapshotRepository
from racket.analytics.sheet import counted_rallies, game_numbers_in_scope
from racket.matches import public as matches


def purge_match(session: Session, match_id: uuid.UUID) -> int:
    """Delete every snapshot of the match (in the caller's transaction). Rows deleted."""
    return SnapshotRepository(session).delete_for_match(match_id)


def snapshot_match_ids(
    session: Session, after: uuid.UUID | None, limit: int
) -> Sequence[uuid.UUID]:
    """Match ids that have snapshot rows, ascending, one page (orphan sweep, SEC-S3-TM-02)."""
    return SnapshotRepository(session).match_ids(after, limit)


@dataclass(frozen=True, slots=True)
class RallyFact:
    """One counted rally (metric-dictionary rules 0.1, 0.2) as plain values (read model)."""

    rally_id: str
    number: int
    game: int
    serving_side: str
    winning_side: str
    ending: str
    fault_kind: str | None
    responsible_player: str | None
    actor: str  # the side that made the ending (rule 0.2)
    point_to: str | None  # the side that scored, None when only the serve moved


@dataclass(frozen=True, slots=True)
class RallyFacts:
    """The counted rallies of a match's games in scope (dictionary AN-04), in play order."""

    sheet_version: int | None
    rules_version: str
    games: tuple[int, ...]
    rallies: tuple[RallyFact, ...]


def facts_of_sheet(sheet: Mapping[str, Any], sheet_version: int | None = None) -> RallyFacts:
    """The read model of a projected score sheet (pure; ``rally_facts`` reads the live one)."""
    games = tuple(game_numbers_in_scope(sheet))
    in_scope = set(games)
    rallies = tuple(
        RallyFact(
            rally_id=r.rally_id,
            number=r.number,
            game=r.game,
            serving_side=r.serving_side,
            winning_side=r.winning_side,
            ending=r.ending,
            fault_kind=r.fault_kind,
            responsible_player=r.responsible_player,
            actor=r.actor,
            point_to=r.point_to,
        )
        for r in counted_rallies(sheet)
        if r.game in in_scope
    )
    return RallyFacts(sheet_version, str(sheet.get("rules_version", "")), games, rallies)


def rally_facts(session: Session, match_id: uuid.UUID) -> RallyFacts | None:
    """The counted rallies of a live match; ``None`` when the match is gone (tombstoned or
    purged). Read-only; the match row stays share-locked until the caller ends its
    transaction (``lock_live_sheet``)."""
    live = matches.lock_live_sheet(session, match_id)
    if live is None:
        return None
    return facts_of_sheet(live.sheet, live.version)
