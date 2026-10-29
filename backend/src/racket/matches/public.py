"""Match & Scoring's published command port for Capture & Media (context map R2).

Sprint 0 exception (ADR 0011, hotspot H3), extended in Sprint 1 with ``reject_video`` and
``clear_rejection`` (ST-018): ``mark_uploaded`` runs inside the upload-completion
transaction, so "upload complete", ``Match.mark_uploaded`` and the probe job commit together.
"""

from __future__ import annotations

import itertools
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from racket.matches.deletion import Tombstone, confirm_deletion
from racket.matches.domain import DEFAULT_RULES_VERSION, MatchId, OwnerId
from racket.matches.repository import MatchRepository, match_participants, matches
from racket.matches.scorebook.domain import (
    CommandContext,
    OutcomeInput,
    RallyTimes,
    Scorebook,
    project,
)
from racket.matches.scorebook.repository import ScorebookRepository, match_rallies
from racket.platform.errors import NotFound
from racket.sports.pickleball.rules import Side
from racket.video_ingest.public import close_for_deleted_match, lock_upload_of_match

__all__ = ["Tombstone", "confirm_deletion"]  # the deletion rules Identity & Players reuses


def owns_match(session: Session, match_id: uuid.UUID, owner_id: uuid.UUID) -> bool:
    return MatchRepository(session).get_owned(MatchId(match_id), OwnerId(owner_id)) is not None


def mark_uploaded(
    session: Session, match_id: uuid.UUID, owner_id: uuid.UUID, media_asset_id: uuid.UUID
) -> None:
    match = MatchRepository(session).get_owned(
        MatchId(match_id), OwnerId(owner_id), for_update=True
    )
    if match is None:
        raise NotFound("match vanished during upload")
    match.mark_uploaded(media_asset_id)


def reject_video(
    session: Session, match_id: uuid.UUID, owner_id: uuid.UUID, code: str, at: datetime
) -> None:
    """Capture & Media refused a file for this match (ST-018; api-sprint-01 §6.6). Runs in the
    caller's transaction, so the refusal and the clean-up commit together."""
    match = MatchRepository(session).get_owned(
        MatchId(match_id), OwnerId(owner_id), for_update=True
    )
    if match is None:
        raise NotFound("match vanished during upload")
    match.reject_video(code, at=at)


def refuse_upload(
    session: Session, match_id: uuid.UUID, owner_id: uuid.UUID, code: str, at: datetime
) -> None:
    """Capture & Media refused a file before receiving it (§6.3, §6.5). 409 when the match
    already has its video (PE-R1-01). Runs in the caller's transaction."""
    match = MatchRepository(session).get_owned(
        MatchId(match_id), OwnerId(owner_id), for_update=True
    )
    if match is None:
        raise NotFound("match vanished during upload")
    match.refuse_upload(code, at=at)


def clear_rejection(session: Session, match_id: uuid.UUID, owner_id: uuid.UUID) -> None:
    """A new upload was created: the last refusal is no longer shown (§5.2)."""
    match = MatchRepository(session).get_owned(
        MatchId(match_id), OwnerId(owner_id), for_update=True
    )
    if match is not None and match.rejection_code is not None:
        match.clear_rejection()


@dataclass(frozen=True)
class LiveSheet:
    """The projected score sheet of a live match at ``version`` (published to Analytics, R6)."""

    version: int
    owner_id: uuid.UUID
    sheet: dict[str, Any]


def lock_live_sheet(session: Session, match_id: uuid.UUID) -> LiveSheet | None:
    """The sheet of a live match, read under the match row ``FOR SHARE`` lock, which the caller
    holds to its commit (analytics-snapshots.md §4.2 step 2, invariant S8). ``None`` when the
    match does not exist or is deleted, so a snapshot is never written for it."""
    owner = session.execute(
        sa.select(matches.c.owner_id)
        .where(*MatchRepository.live(match_id))
        .with_for_update(read=True)
    ).scalar_one_or_none()
    if owner is None:
        return None
    book = ScorebookRepository(session).load(match_id)
    return LiveSheet(book.version, uuid.UUID(str(owner)), project(book))


def lock_live_match(session: Session, match_id: uuid.UUID) -> bool:
    """The live match row ``FOR SHARE`` until the caller commits, so a row another context keys
    by this match (the consent record, ST-052b) is written before a deletion or after it, never
    across it (deletion-and-purge.md §3.3). ``False`` when the match does not exist or is
    deleted: the caller writes nothing (PE-052b-R1-01)."""
    found = session.execute(
        sa.select(matches.c.id).where(*MatchRepository.live(match_id)).with_for_update(read=True)
    ).first()
    return found is not None


@dataclass(frozen=True)
class DueMatch:
    match_id: uuid.UUID
    owner_id: uuid.UUID
    deleted_at: datetime


def due_for_purge(
    session: Session, limit: int, *, older_than: datetime | None = None
) -> list[DueMatch]:
    """Tombstoned matches, oldest deletion first (deletion-and-purge.md §4.2)."""
    query = sa.select(matches.c.id, matches.c.owner_id, matches.c.deleted_at).where(
        matches.c.deleted_at.is_not(None)
    )
    if older_than is not None:
        query = query.where(matches.c.deleted_at <= older_than)
    rows = session.execute(query.order_by(matches.c.deleted_at, matches.c.id).limit(limit)).all()
    return [DueMatch(uuid.UUID(str(r.id)), uuid.UUID(str(r.owner_id)), r.deleted_at) for r in rows]


def claim_for_purge(session: Session, match_id: uuid.UUID) -> bool:
    """Lock one tombstoned match for this pass; ``False`` when another pass holds it or it is
    gone (``FOR UPDATE SKIP LOCKED``, so parallel passes split the work, IT-03-07)."""
    found = session.execute(
        sa.select(matches.c.id)
        .where(matches.c.id == match_id, matches.c.deleted_at.is_not(None))
        .with_for_update(skip_locked=True)
    ).first()
    return found is not None


def purge_match(session: Session, match_id: uuid.UUID) -> int:
    """Delete the match root of a claimed tombstone; the foreign keys cascade to participants,
    games, rallies and the correction trail. Runs last, in the caller's transaction."""
    result = session.execute(
        sa.delete(matches).where(matches.c.id == match_id, matches.c.deleted_at.is_not(None))
    )
    return int(result.rowcount)  # type: ignore[attr-defined]


def existing_ids(session: Session, ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """Which of ``ids`` still have a ``matches`` row, live or tombstoned (orphan sweep)."""
    if not ids:
        return set()
    found = session.execute(sa.select(matches.c.id).where(matches.c.id.in_(ids))).scalars()
    return {uuid.UUID(str(i)) for i in found}


def live_ids(session: Session, ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """Which of ``ids`` are live matches (not tombstoned): the upload expiry leaves the uploads
    of a deleted match to that match's purge (ST-038; deletion-and-purge.md §4.4, §4.6)."""
    if not ids:
        return set()
    found = session.execute(
        sa.select(matches.c.id).where(matches.c.id.in_(ids), matches.c.deleted_at.is_(None))
    ).scalars()
    return {uuid.UUID(str(i)) for i in found}


def tombstone_owned_by(session: Session, owner_id: uuid.UUID, at: datetime) -> list[uuid.UUID]:
    """Tombstone every live match of an owner and close their uploads, in the caller's
    transaction (``DELETE /me`` step 3; the pass's second net, SEC-S3-TM-05). Returns the ids.

    One match at a time, in the global lock order (deletion-and-purge.md §3.1): its upload row,
    then its match row, as ``DELETE /matches/{id}`` and the completing tus PATCH take them, so
    none of them deadlocks with this (SQA-051-01). Ids in a fixed order; a match tombstoned by a
    parallel request meanwhile is skipped."""
    live = session.execute(
        sa.select(matches.c.id).where(
            matches.c.owner_id == owner_id, matches.c.deleted_at.is_(None)
        )
    ).scalars()
    ids: list[uuid.UUID] = []
    for match_id in sorted(uuid.UUID(str(i)) for i in live):
        lock_upload_of_match(session, match_id)
        tombstoned = session.execute(
            sa.update(matches)
            .where(matches.c.id == match_id, matches.c.deleted_at.is_(None))
            .values(deleted_at=at, updated_at=at)
            .returning(matches.c.id)
        ).scalars()
        if list(tombstoned):
            close_for_deleted_match(session, match_id, at)
            ids.append(match_id)
    return ids


def owner_has_matches(session: Session, owner_id: uuid.UUID) -> bool:
    """Any ``matches`` row (live or tombstoned) of this owner: an account is purged only after
    every one of its matches (deletion-and-purge.md §4.2)."""
    found = session.execute(sa.select(matches.c.id).where(matches.c.owner_id == owner_id).limit(1))
    return found.first() is not None


@dataclass(frozen=True)
class TaggedMatch:
    """A live match with its owner and its count of standing (not withdrawn) rallies."""

    match_id: uuid.UUID
    owner_id: uuid.UUID
    rallies: int


def live_matches_with_rallies(
    session: Session, extra_ids: Iterable[uuid.UUID] = ()
) -> list[TaggedMatch]:
    """FR-009 (ST-070; context map R9): every live match that has a standing rally, plus each
    live match of ``extra_ids`` (e.g. one with Full Tag labels only), for the label-set build.
    Ids and counts only; ordered by match id. A tombstoned match is never listed."""
    standing = (
        sa.select(match_rallies.c.match_id, sa.func.count().label("rallies"))
        .where(match_rallies.c.withdrawn.is_(False))
        .group_by(match_rallies.c.match_id)
        .subquery()
    )
    extra = list(extra_ids)
    rows = session.execute(
        sa.select(matches.c.id, matches.c.owner_id, sa.func.coalesce(standing.c.rallies, 0))
        .select_from(matches.outerjoin(standing, standing.c.match_id == matches.c.id))
        .where(
            matches.c.deleted_at.is_(None),
            sa.or_(standing.c.rallies.is_not(None), matches.c.id.in_(extra)),
        )
        .order_by(matches.c.id)
    ).all()
    return [TaggedMatch(uuid.UUID(str(r[0])), uuid.UUID(str(r[1])), int(r[2])) for r in rows]


def owned_format(session: Session, match_id: uuid.UUID, owner_id: uuid.UUID) -> str | None:
    """The format (``singles``/``doubles``) of a live match the owner holds, else ``None``: the
    owner filter for another context's routes that also need the slots (Full Tag)."""
    match = MatchRepository(session).get_owned(MatchId(match_id), OwnerId(owner_id))
    return None if match is None else match.format.value


def player_sides(session: Session, owner_id: uuid.UUID) -> list[tuple[uuid.UUID, str | None]]:
    """The owner's live matches with the side of the participant marked ``is_me`` (``A`` or
    ``B``), or ``None`` when no participant is "me" (ST-055; coaching-plan.md §3, §4). Ordered
    by ``(played_on, id)``, undated matches last."""
    me = (
        sa.select(match_participants.c.match_id, match_participants.c.slot)
        .where(match_participants.c.is_me.is_(True))
        .subquery()
    )
    rows = session.execute(
        sa.select(matches.c.id, me.c.slot)
        .select_from(matches.outerjoin(me, me.c.match_id == matches.c.id))
        .where(matches.c.owner_id == owner_id, matches.c.deleted_at.is_(None))
        .order_by(matches.c.played_on.asc().nulls_last(), matches.c.id)
    ).all()
    return [(uuid.UUID(str(r.id)), None if r.slot is None else str(r.slot)[0]) for r in rows]


def lock_scope_versions(
    session: Session, owner_id: uuid.UUID
) -> tuple[tuple[uuid.UUID, str | None, int, str, str, int], ...]:
    """The owner's live matches as ``(id, is_me side or None, scorebook version, rules version,
    format, best of)`` in match id order, each match row ``FOR SHARE`` to the caller's commit,
    as ``lock_live_sheet`` holds it (SRE-VERIFY04R3-01: Coaching's scope key). Every scorebook
    command bumps ``version``, so an equal key means equal sheets."""
    me = (
        sa.select(match_participants.c.match_id, match_participants.c.slot)
        .where(match_participants.c.is_me.is_(True))
        .subquery()
    )
    rows = session.execute(
        sa.select(
            matches.c.id,
            me.c.slot,
            matches.c.version,
            matches.c.rules_version,
            matches.c.format,
            matches.c.best_of,
        )
        .select_from(matches.outerjoin(me, me.c.match_id == matches.c.id))
        .where(matches.c.owner_id == owner_id, matches.c.deleted_at.is_(None))
        .order_by(matches.c.id)
        .with_for_update(read=True, of=matches)
    ).all()
    return tuple(
        (
            uuid.UUID(str(r.id)),
            None if r.slot is None else str(r.slot)[0],
            int(r.version),
            str(r.rules_version),
            str(getattr(r.format, "value", r.format)),
            int(r.best_of),
        )
        for r in rows
    )


def sheet_of_tags(
    games: Iterable[Mapping[str, Any]],
    *,
    format: str = "doubles",
    best_of: int = 3,
    rules_version: str = DEFAULT_RULES_VERSION,
) -> dict[str, Any]:
    """The projected score sheet of a Quick Tag script, played through the scorebook's own
    commands (``start_game``, ``tag``), so whatever they refuse is refused here (ST-060 eval
    cases). ``games``: ``[{"first_serving_side": "A", "tags": [{"winning_side": ...,
    "ending": ..., "fault_kind": ..., "responsible_player": ...}, ...]}, ...]``. Pure and
    deterministic: ids count up from 1, rallies are 3 s long, 1 s apart."""
    ids = itertools.count(1)
    ctx = CommandContext(
        actor_id=uuid.UUID(int=0),
        at=datetime(2026, 1, 1, tzinfo=UTC),
        new_id=lambda: uuid.UUID(int=next(ids)),
    )
    book = Scorebook.new(rules_version=rules_version, format=format, best_of=best_of)
    start = 0
    for game in games:
        book = book.start_game(
            first_serving_side=Side(game["first_serving_side"]),
            ends_switched=False,
            ready=True,
            expected_version=book.version,
            ctx=ctx,
        )
        for tag in game["tags"]:
            outcome = OutcomeInput.parse(
                {k: v for k, v in tag.items() if v is not None}, format=format
            )
            times = RallyTimes.parse(start, start + 3_000)
            book, _ = book.tag(times, outcome, ready=True, expected_version=book.version, ctx=ctx)
            start += 4_000
    return project(book)
