"""Persistence for the ``Match`` aggregate (ST-006). Imperative mapping keeps the domain pure."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from racket.matches.domain import (
    Match,
    MatchFormat,
    MatchId,
    MatchParticipant,
    MatchStatus,
    OwnerId,
    Participants,
)
from racket.platform.db import IdType, StrEnumType, mapper_registry, metadata

matches = sa.Table(
    "matches",
    metadata,
    sa.Column("id", IdType(MatchId), primary_key=True),
    sa.Column("owner_id", IdType(OwnerId), nullable=False),
    sa.Column("title", sa.String(120), nullable=False),
    sa.Column("format", StrEnumType(MatchFormat), nullable=False),
    sa.Column("status", StrEnumType(MatchStatus), nullable=False),
    sa.Column("media_asset_id", sa.Uuid(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("scoring_system", sa.String(32), nullable=False),
    sa.Column("rules_version", sa.String(64), nullable=False),
    sa.Column("played_on", sa.Date(), nullable=True),
    sa.Column("rejection_code", sa.String(32), nullable=True),
    sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
    # The scorebook's optimistic lock and match length (ST-026; read by its repository only).
    sa.Column("best_of", sa.SmallInteger(), nullable=False, server_default="3"),
    sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
)

match_participants = sa.Table(
    "match_participants",
    metadata,
    sa.Column("match_id", sa.Uuid(), sa.ForeignKey("matches.id", ondelete="CASCADE"),
              primary_key=True),
    sa.Column("slot", sa.String(2), primary_key=True),
    sa.Column("nickname", sa.String(30), nullable=False),
    sa.Column("is_me", sa.Boolean(), nullable=False),
)  # fmt: skip

# ``participants`` is a value of the aggregate, not a column: the repository saves and loads it.
mapper_registry.map_imperatively(
    Match, matches, exclude_properties=["participants", "best_of", "version"]
)


class MatchRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, match: Match) -> None:
        self.session.add(match)
        if match.participants is not None:
            self.session.flush()  # the match row first: participants reference it
            self.session.execute(
                sa.insert(match_participants),
                [
                    {"match_id": match.id.value, "slot": m.slot, "nickname": m.nickname,
                     "is_me": m.is_me}
                    for m in match.participants.members
                ],
            )  # fmt: skip

    def _with_participants(self, found: list[Match]) -> list[Match]:
        """Load the participant values of these matches in one query (ADR 0024)."""
        if not found:
            return found
        rows = self.session.execute(
            sa.select(match_participants).where(
                match_participants.c.match_id.in_([m.id.value for m in found])
            )
        ).all()
        by_match: dict[object, list[MatchParticipant]] = {}
        for row in rows:
            by_match.setdefault(row.match_id, []).append(
                MatchParticipant(row.slot, row.nickname, row.is_me)
            )
        for match in found:
            members = by_match.get(match.id.value)
            if members:
                order = ("A1", "A2", "B1", "B2")
                members.sort(key=lambda m: order.index(m.slot))
                match.participants = Participants(match.format.value, tuple(members))
            else:
                match.participants = None
        return found

    @staticmethod
    def live(match_id: object) -> tuple[Any, ...]:
        """The filter of a match that is still there (one place for every read, R1)."""
        value = match_id.value if isinstance(match_id, MatchId) else match_id
        return (matches.c.id == value,)

    def get_owned(
        self, match_id: MatchId, owner_id: OwnerId, *, for_update: bool = False
    ) -> Match | None:
        """The ownership-loading pattern ``WHERE id = :id AND owner_id = :me`` (R1)."""
        query = sa.select(Match).where(matches.c.id == match_id, matches.c.owner_id == owner_id)
        if for_update:
            query = query.with_for_update()
        match = self.session.execute(query).scalar_one_or_none()
        return None if match is None else self._with_participants([match])[0]

    def list_for_owner(self, owner_id: OwnerId, limit: int) -> list[Match]:
        query = (
            sa.select(Match)
            .where(matches.c.owner_id == owner_id)
            .order_by(matches.c.created_at.desc(), matches.c.id)
            .limit(limit)
        )
        return self._with_participants(list(self.session.execute(query).scalars()))
