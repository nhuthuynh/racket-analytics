"""Persistence of the scorebook (ST-026; match-aggregate §6). Only ``racket.matches`` reads
these tables (context map rule 1). The repository loads and saves the whole scored part of one
match; the ``matches`` row lock and ``version`` make every command all-or-nothing and
serialised per match (IT-02-02, IT-02-04).
"""

from __future__ import annotations

import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from racket.matches.repository import MatchRepository, matches
from racket.matches.scorebook.domain import (
    Change,
    Ending,
    GameStart,
    OutcomeInput,
    Rally,
    RallyTimes,
    Scorebook,
    StaleMatch,
)
from racket.platform.db import metadata
from racket.platform.errors import NotFound
from racket.sports.pickleball.rules import FaultKind, Side


class MatchGone(NotFound):
    pass


def _match_fk() -> sa.ForeignKey:
    return sa.ForeignKey("matches.id", ondelete="CASCADE")


match_games = sa.Table(
    "match_games",
    metadata,
    sa.Column("match_id", sa.Uuid(), _match_fk(), primary_key=True),
    sa.Column("number", sa.SmallInteger(), primary_key=True),
    sa.Column("first_serving_side", sa.String(1), nullable=False),
    sa.Column("ends_switched", sa.Boolean(), nullable=False),
    sa.Column("created_version", sa.Integer(), nullable=False),
)

match_rallies = sa.Table(
    "match_rallies",
    metadata,
    sa.Column("id", sa.Uuid(), primary_key=True),
    sa.Column("match_id", sa.Uuid(), _match_fk(), nullable=False),
    sa.Column("game_number", sa.SmallInteger(), nullable=False),
    sa.Column("seq", sa.Integer(), nullable=False),
    sa.Column("start_ms", sa.BigInteger(), nullable=False),
    sa.Column("end_ms", sa.BigInteger(), nullable=False),
    sa.Column("ending", sa.String(16), nullable=False),
    sa.Column("winning_side", sa.String(1), nullable=True),
    sa.Column("responsible_player", sa.String(2), nullable=True),
    sa.Column("fault_kind", sa.String(16), nullable=True),
    sa.Column("withdrawn", sa.Boolean(), nullable=False),
    sa.Column("created_version", sa.Integer(), nullable=False),
)

match_corrections = sa.Table(
    "match_corrections",
    metadata,
    sa.Column("id", sa.Uuid(), primary_key=True),
    sa.Column("match_id", sa.Uuid(), _match_fk(), nullable=False),
    sa.Column("version", sa.Integer(), nullable=False),
    sa.Column("kind", sa.String(16), nullable=False),
    sa.Column("actor_id", sa.Uuid(), nullable=False),
    sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("rally_id", sa.Uuid(), nullable=True),
    sa.Column("game_number", sa.SmallInteger(), nullable=True),
    sa.Column("field", sa.String(32), nullable=True),
    sa.Column("old_value", JSONB(none_as_null=True), nullable=True),
    sa.Column("new_value", JSONB(none_as_null=True), nullable=True),
    sa.Column("undoes", sa.Uuid(), nullable=True),
)


def _rally_row(match_id: uuid.UUID, rally: Rally) -> dict[str, Any]:
    return {
        "id": rally.id,
        "match_id": match_id,
        "game_number": rally.game_number,
        "seq": rally.seq,
        "start_ms": rally.times.start_ms,
        "end_ms": rally.times.end_ms,
        **rally.outcome.as_json(),
        "withdrawn": rally.withdrawn,
        "created_version": rally.created_version,
    }


def _stored_outcome(row: Any) -> OutcomeInput:
    """Stored inputs are not re-validated: a rule refined later must never make an old
    match unreadable (the projection marks what the engine refuses, §5 "Errors")."""
    return OutcomeInput(
        Ending(row.ending),
        None if row.winning_side is None else Side(row.winning_side),
        row.responsible_player,
        None if row.fault_kind is None else FaultKind(row.fault_kind),
    )


class ScorebookRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def load(self, match_id: uuid.UUID, *, lock: bool = False) -> Scorebook:
        """The scorebook of a match the caller has already loaded as its owner. ``lock`` takes
        the match row lock first, so commands on one match run one at a time (IT-02-04)."""
        query = sa.select(
            matches.c.rules_version, matches.c.format, matches.c.best_of, matches.c.version
        ).where(*MatchRepository.live(match_id))
        head = self.session.execute(query.with_for_update() if lock else query).one_or_none()
        if head is None:  # deleted after the owner filter ran (ST-050; IT-03-12 race)
            raise MatchGone("the match was deleted")
        fmt = str(getattr(head.format, "value", head.format))
        games = tuple(
            GameStart(r.number, Side(r.first_serving_side), r.ends_switched, r.created_version)
            for r in self.session.execute(
                sa.select(match_games)
                .where(match_games.c.match_id == match_id)
                .order_by(match_games.c.number)
            )
        )
        rallies = tuple(
            Rally(
                id=r.id,
                game_number=r.game_number,
                seq=r.seq,
                times=RallyTimes(r.start_ms, r.end_ms),
                outcome=_stored_outcome(r),
                created_version=r.created_version,
                withdrawn=r.withdrawn,
            )
            for r in self.session.execute(
                sa.select(match_rallies)
                .where(match_rallies.c.match_id == match_id)
                .order_by(match_rallies.c.seq)
            )
        )
        changes = tuple(
            Change(
                id=r.id,
                kind=r.kind,
                version=r.version,
                actor_id=r.actor_id,
                at=r.at,
                rally_id=r.rally_id,
                game_number=r.game_number,
                field=r.field,
                old_value=r.old_value,
                new_value=r.new_value,
                undoes=r.undoes,
            )
            for r in self.session.execute(
                sa.select(match_corrections)
                .where(match_corrections.c.match_id == match_id)
                .order_by(match_corrections.c.version, match_corrections.c.at)
            )
        )
        return Scorebook(
            rules_version=head.rules_version,
            format=fmt,
            best_of=head.best_of,
            version=head.version,
            games=games,
            rallies=rallies,
            changes=changes,
        )

    def save(self, match_id: uuid.UUID, before: Scorebook, after: Scorebook) -> None:
        """Write the difference; nothing is committed here (the service owns the transaction).
        The version update is conditional, so a lost race can never overwrite (IT-02-04)."""
        bumped = self.session.execute(
            sa.update(matches)
            .where(matches.c.id == match_id, matches.c.version == before.version)
            .values(version=after.version)
        )
        if bumped.rowcount != 1:  # type: ignore[attr-defined]
            raise StaleMatch("version changed while saving")
        old_games = {g.number for g in before.games}
        new_games = {g.number: g for g in after.games}
        gone = old_games - set(new_games)
        if gone:
            self.session.execute(
                sa.delete(match_games).where(
                    match_games.c.match_id == match_id, match_games.c.number.in_(gone)
                )
            )
        added = [g for n, g in new_games.items() if n not in old_games]
        if added:
            self.session.execute(
                sa.insert(match_games),
                [
                    {
                        "match_id": match_id,
                        "number": g.number,
                        "first_serving_side": g.first_serving_side.value,
                        "ends_switched": g.ends_switched,
                        "created_version": g.created_version,
                    }
                    for g in added
                ],
            )
        old_rallies = {r.id: r for r in before.rallies}
        fresh = [_rally_row(match_id, r) for r in after.rallies if r.id not in old_rallies]
        if fresh:
            self.session.execute(sa.insert(match_rallies), fresh)
        for rally in after.rallies:
            if rally.id in old_rallies and old_rallies[rally.id] != rally:
                row = _rally_row(match_id, rally)
                self.session.execute(
                    sa.update(match_rallies)
                    .where(match_rallies.c.id == rally.id)
                    .values({k: v for k, v in row.items() if k not in ("id", "match_id")})
                )
        known = {c.id for c in before.changes}
        trail = [c for c in after.changes if c.id not in known]
        if trail:
            self.session.execute(
                sa.insert(match_corrections),
                [
                    {
                        "id": c.id,
                        "match_id": match_id,
                        "version": c.version,
                        "kind": c.kind,
                        "actor_id": c.actor_id,
                        "at": c.at,
                        "rally_id": c.rally_id,
                        "game_number": c.game_number,
                        "field": c.field,
                        "old_value": c.old_value,
                        "new_value": c.new_value,
                        "undoes": c.undoes,
                    }
                    for c in trail
                ],
            )
