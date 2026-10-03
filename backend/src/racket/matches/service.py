"""Match application service (ST-006): commands on ``Match`` and its read model.

The status and media shown to the player are a read model composed from ``Match`` and
Capture & Media's ``media_summary`` port (context map R2; api-sprint-00 §5.1).
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from racket.matches.domain import InvalidId, Match, MatchId, MatchStatus, OwnerId
from racket.matches.repository import MatchRepository
from racket.matches.schemas import MatchOut, MediaOut
from racket.platform.errors import NotFound
from racket.platform.logs import SECURITY_LOGGER
from racket.video_ingest.domain import UploadStatus
from racket.video_ingest.public import media_summary

security_log = logging.getLogger(SECURITY_LOGGER)
log = logging.getLogger(__name__)


class MatchNotFound(NotFound):
    pass


def _rfc3339(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


class MatchService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.matches = MatchRepository(session)

    def create(self, owner: OwnerId, title: str, format: str) -> Match:
        match = Match.create(owner_id=owner, title=title, format=format)
        self.matches.add(match)
        self.session.commit()
        log.info("match created", extra={"event": "match.created", "match_id": str(match.id)})
        return match

    def list_for_owner(self, owner: OwnerId, limit: int) -> list[Match]:
        return self.matches.list_for_owner(owner, limit)

    def get_owned(self, raw_id: str, owner: OwnerId, *, route: str, method: str) -> Match:
        """One ownership check for every ID route; "missing" and "not yours" look the same."""
        try:
            match_id = MatchId(raw_id)
        except InvalidId:
            match = None
        else:
            match = self.matches.get_owned(match_id, owner)
        if match is None:
            security_log.info(
                "access denied",
                extra={"event": "authz.denied", "account_id": str(owner), "route": route,
                       "method": method},
            )  # fmt: skip
            raise MatchNotFound("no such match for this owner")
        return match

    def view(self, match: Match) -> MatchOut:
        summary = media_summary(self.session, match.id.value)
        if summary.probe_failed:
            status = "probe_failed"
        elif match.status is MatchStatus.VIDEO_RECEIVED:
            status = "video_received"
        elif summary.upload_state is UploadStatus.RECEIVING:
            status = "uploading"
        else:
            status = "awaiting_upload"
        facts = summary.facts
        media = None if facts is None else MediaOut(**vars(facts))
        return MatchOut(
            id=str(match.id),
            title=match.title,
            format=match.format.value,
            status=status,  # type: ignore[arg-type]
            media=media,
            created_at=_rfc3339(match.created_at),
            updated_at=_rfc3339(match.updated_at),
        )
