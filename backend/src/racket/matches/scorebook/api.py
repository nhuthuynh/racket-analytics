"""Scorebook HTTP routes (ST-027, ST-030; routes and fields as ``scripts/measure/tagcontract.py``
until ``api-sprint-02.md`` exists, blockers.md 2026-10-05). Every route loads the match through
the one ownership dependency ``owned_match`` (404 for anyone else, I9) [AQS/SEC-09].

Commands carry the client's last version in ``If-Match`` and answer ``{"version", "sheet"}``;
the sheet itself never holds the version, so an undo can restore it byte for byte (C-04,
BE-D1-04). ``GET …/score-sheet`` returns the version as the ``ETag``.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from racket.matches.api import OwnedMatch
from racket.matches.scorebook.domain import MatchNotReady, project
from racket.matches.scorebook.service import ScorebookService, parse_version
from racket.platform.db import get_session
from racket.players.api import CurrentAccount, presented_token
from racket.video_ingest.public import media_link

router = APIRouter()


def get_scorebook_service(
    request: Request, session: Annotated[Session, Depends(get_session)]
) -> ScorebookService:
    """ADR 0012 seam: tests override this to make the service fail (IT-02-02)."""
    return ScorebookService(session)


Service = Annotated[ScorebookService, Depends(get_scorebook_service)]
IfMatch = Annotated[str | None, Header(alias="If-Match")]
JsonBody = Annotated[Any, Body()]


def _etag(version: int) -> dict[str, str]:
    return {"ETag": f'"{version}"'}


@router.get("/matches/{match_id}/score-sheet")
def get_score_sheet(match: OwnedMatch, service: Service) -> JSONResponse:
    """FR-049, FR-055: every rally with server, score before and after, winner and ending."""
    version, sheet = service.sheet(match)
    return JSONResponse(sheet, headers=_etag(version))


@router.post("/matches/{match_id}/games", status_code=201)
def start_game(
    match: OwnedMatch,
    account: CurrentAccount,
    service: Service,
    body: JsonBody,
    if_match: IfMatch = None,
) -> JSONResponse:
    version = parse_version(if_match)
    book = service.start_game(match, account.id, body, version)
    return JSONResponse(
        {"version": book.version, "sheet": project(book)},
        status_code=201,
        headers=_etag(book.version),
    )


@router.post("/matches/{match_id}/rallies", status_code=201)
def tag_rally(
    match: OwnedMatch,
    account: CurrentAccount,
    service: Service,
    body: JsonBody,
    if_match: IfMatch = None,
) -> JSONResponse:
    """FR-050: one tag; the response carries the new projection (NFR-012 server half)."""
    version = parse_version(if_match)
    book, rally_id = service.tag(match, account.id, body, version)
    body_out = {"version": book.version, "rally_id": str(rally_id), "sheet": project(book)}
    return JSONResponse(body_out, status_code=201, headers=_etag(book.version))


@router.patch("/matches/{match_id}/rallies/{rally_id}")
def correct_rally(
    rally_id: str,
    match: OwnedMatch,
    account: CurrentAccount,
    service: Service,
    body: JsonBody,
    if_match: IfMatch = None,
) -> JSONResponse:
    """FR-052, FR-053: one field of one rally; later rallies are re-scored in the same step."""
    version = parse_version(if_match)
    book = service.correct(match, account.id, rally_id, body, version)
    return JSONResponse(
        {"version": book.version, "sheet": project(book)}, headers=_etag(book.version)
    )


@router.post("/matches/{match_id}/undo")
def undo(
    match: OwnedMatch, account: CurrentAccount, service: Service, if_match: IfMatch = None
) -> JSONResponse:
    """FR-052: reverse the newest change; audited (C-04: the sheet is restored byte for byte)."""
    version = parse_version(if_match)
    book = service.undo(match, account.id, version)
    return JSONResponse(
        {"version": book.version, "sheet": project(book)}, headers=_etag(book.version)
    )


@router.get("/matches/{match_id}/corrections")
def correction_history(match: OwnedMatch, service: Service) -> dict[str, Any]:
    return {"items": service.history(match)}


@router.post("/matches/{match_id}/rallies/{rally_id}/resolution")
def resolve_rally(
    rally_id: str,
    match: OwnedMatch,
    account: CurrentAccount,
    service: Service,
    body: JsonBody,
    if_match: IfMatch = None,
) -> JSONResponse:
    """FR-053 (a), provisional (match-aggregate §8 Q1): withdraw a "needs your decision" rally,
    or move it to the next game. Never deletes it."""
    version = parse_version(if_match)
    book = service.resolve(match, account.id, rally_id, body, version)
    return JSONResponse(
        {"version": book.version, "sheet": project(book)}, headers=_etag(book.version)
    )


@router.get("/matches/{match_id}/rallies/{rally_id}/media")
def rally_media(
    rally_id: str,
    match: OwnedMatch,
    service: Service,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> JSONResponse:
    """FR-027, NFR-055: a fresh presigned link to the match video, valid at most 15 minutes,
    with the rally's start; never the session token in the URL, never logged (NFR-069)."""
    start_ms = service.rally_start(match, rally_id)
    settings = request.app.state.settings
    link = media_link(
        session,
        request.app.state.object_store(),
        settings,
        match.id.value,
        session_token=presented_token(request),
    )
    if link is None:
        raise MatchNotReady("no received video")
    body = {"url": link.url, "expires_in_s": link.expires_in_s, "start_ms": start_ms}
    return JSONResponse(
        body, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
    )
