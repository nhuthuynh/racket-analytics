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
from racket.matches.scorebook.domain import project
from racket.matches.scorebook.service import ScorebookService, parse_version
from racket.platform.db import get_session
from racket.players.api import CurrentAccount

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
