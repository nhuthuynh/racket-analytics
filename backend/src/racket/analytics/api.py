"""Stats HTTP routes (ST-046, ST-047; api-sprint-03 §2, §3; FR-100..FR-103, FR-055).

Every route checks ownership through Match & Scoring's port before anything else (R1; NFR-051):
another account's match, an unknown, malformed or deleted id all answer the same 404.
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from racket.analytics import service
from racket.analytics.evidence import EvidenceQuery, evidence_page
from racket.analytics.snapshot import DEFAULT_MAX_INTERVAL_WIDTH
from racket.matches import public as matches
from racket.platform.db import get_session
from racket.platform.errors import NotFound
from racket.platform.logs import SECURITY_LOGGER
from racket.players.api import CurrentAccount
from racket.sports.pickleball import metrics

router = APIRouter()
security_log = logging.getLogger(SECURITY_LOGGER)
NO_STORE = {"Cache-Control": "no-store"}
DbSession = Annotated[Session, Depends(get_session)]


class StatsNotFound(NotFound):
    pass


def owned_match_id(
    match_id: str, request: Request, account: CurrentAccount, session: DbSession
) -> uuid.UUID:
    try:
        parsed = uuid.UUID(match_id)
    except ValueError:
        parsed = None
    if parsed is None or not matches.owns_match(session, parsed, account.id):
        security_log.info(
            "access denied",
            extra={"event": "authz.denied", "account_id": str(account.id),
                   "route": getattr(request.scope.get("route"), "path", ""),
                   "method": request.method},
        )  # fmt: skip
        raise StatsNotFound("no such match for this owner")
    session.rollback()  # end the ownership read; the stats read takes its own lock
    return parsed


OwnedMatchId = Annotated[uuid.UUID, Depends(owned_match_id)]


def _current(session: Session, match_id: uuid.UUID) -> service.CurrentStats:
    found = service.current(session, match_id, trigger="read")
    if found is None:  # deleted between the ownership check and the read
        raise StatsNotFound("match is gone")
    return found


@router.get("/matches/{match_id}/stats")
def get_stats(match_id: OwnedMatchId, session: DbSession) -> JSONResponse:
    """FR-100..FR-102: the published metrics of the live sheet (read repair, never stale)."""
    found = _current(session, match_id)
    dictionary = metrics.load_dictionary()
    body: dict[str, Any] = {
        "match_id": str(match_id),
        "sheet_version": found.sheet_version,
        "rules_version": found.snapshot.key.rules_version,
        "metric_def_version": found.snapshot.key.metric_def_version,
        "unofficial": bool(found.sheet.get("unofficial", True)),
        "label": found.sheet.get("label"),
        "low_sample_rule": {"max_interval_width": DEFAULT_MAX_INTERVAL_WIDTH},
        "metrics": found.snapshot.published_view(dictionary),
    }
    return JSONResponse(body, headers=NO_STORE)


@router.get("/matches/{match_id}/stats/{metric_id}/evidence")
def get_evidence(
    match_id: OwnedMatchId,
    metric_id: str,
    session: DbSession,
    side: Annotated[str | None, Query()] = None,
    limit: Annotated[str | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
) -> JSONResponse:
    """FR-103: up to 10 rallies behind a published metric and side, "see all n" by cursor.
    An unpublished metric id (unknown, draft, deprecated) is the same 404 as a missing one."""
    if not metrics.load_dictionary().is_published(metric_id):
        raise StatsNotFound("no such published metric")
    query = EvidenceQuery.parse(side=side, limit=limit, cursor=cursor)
    found = _current(session, match_id)
    items, total, next_cursor = evidence_page(
        found.sheet.get("rows", ()), found.snapshot.rallies(metric_id, query.side), query
    )
    body = {
        "metric_id": metric_id,
        "side": query.side,
        "total": total,
        "sheet_version": found.sheet_version,
        "items": items,
        "next_cursor": next_cursor,
    }
    return JSONResponse(body, headers=NO_STORE)
