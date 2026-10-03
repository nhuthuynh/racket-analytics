"""Persistence for the ``Match`` aggregate (ST-006). Imperative mapping keeps the domain pure."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Session

from racket.matches.domain import Match, MatchFormat, MatchId, MatchStatus, OwnerId
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
)

mapper_registry.map_imperatively(Match, matches)


class MatchRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, match: Match) -> None:
        self.session.add(match)

    def get_owned(
        self, match_id: MatchId, owner_id: OwnerId, *, for_update: bool = False
    ) -> Match | None:
        """The ownership-loading pattern ``WHERE id = :id AND owner_id = :me`` (R1)."""
        query = sa.select(Match).where(matches.c.id == match_id, matches.c.owner_id == owner_id)
        if for_update:
            query = query.with_for_update()
        return self.session.execute(query).scalar_one_or_none()

    def list_for_owner(self, owner_id: OwnerId, limit: int) -> list[Match]:
        query = (
            sa.select(Match)
            .where(matches.c.owner_id == owner_id)
            .order_by(matches.c.created_at.desc(), matches.c.id)
            .limit(limit)
        )
        return list(self.session.execute(query).scalars())
