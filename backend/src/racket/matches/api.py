"""Match HTTP routes (ST-006; api-sprint-00 §5). Every ``{match_id}`` route loads the match
through the one ownership dependency ``owned_match`` [AQS/SEC-09; AQS/STACK-01 G7.5]."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from racket.matches.domain import Match, OwnerId
from racket.matches.schemas import MatchList, MatchOut, MediaOut
from racket.matches.service import MatchService
from racket.platform.db import get_session
from racket.players.api import CurrentAccount

router = APIRouter()


def get_match_service(
    request: Request, session: Annotated[Session, Depends(get_session)]
) -> MatchService:
    """ADR 0012 seam: tests override this to make the service fail."""
    return MatchService(session, request.app.state.settings.api_public_path_prefix)


Service = Annotated[MatchService, Depends(get_match_service)]


def owned_match(
    match_id: str, request: Request, account: CurrentAccount, service: Service
) -> Match:
    route = getattr(request.scope.get("route"), "path", "")
    return service.get_owned(match_id, OwnerId(account.id), route=route, method=request.method)


OwnedMatch = Annotated[Match, Depends(owned_match)]


@router.post("/matches", status_code=201)
def create_match(
    body: Annotated[Any, Body()], account: CurrentAccount, service: Service, response: Response
) -> MatchOut:
    """The body is validated by the domain (``MatchSetup``), so every field problem gets its
    code from api-sprint-01 §4.2 in form order (§5.3), never pydantic's first error."""
    match = service.create(OwnerId(account.id), body)
    response.headers["Location"] = f"/matches/{match.id}"
    return service.view(match)


@router.get("/matches")
def list_matches(
    account: CurrentAccount,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> MatchList:
    matches = service.list_for_owner(OwnerId(account.id), limit)
    return MatchList(items=[service.view(m) for m in matches])


@router.get("/matches/{match_id}")
def get_match(match: OwnedMatch, service: Service) -> MatchOut:
    return service.view(match)


@router.delete("/matches/{match_id}", status_code=202)
def delete_match(
    match: OwnedMatch, service: Service, body: Annotated[Any, Body()] = None
) -> JSONResponse:
    """FR-006 (api-sprint-03 §4.1): 202 once hidden; the purge removes every row and object
    by ``purge_due_by``. 404 for anyone else and for an already deleted match."""
    tombstone = service.delete(match, body)
    return JSONResponse(
        tombstone.response(), status_code=202, headers={"Cache-Control": "no-store"}
    )


@router.get(
    "/matches/{match_id}/media",
    response_model=MediaOut,
    responses={204: {"description": "The video is not probed yet"}},
)
def get_match_media(match: OwnedMatch, service: Service) -> Response:
    """200 with the facts, or 204 while the owner's video is not probed yet.

    api-sprint-00 §5.2/§7 (amended for R1-07): "not probed yet" must differ from "not yours",
    because the BOLA matrix's positive control needs a non-404 for the owner on every ID route.
    """
    media = service.view(match).media
    if media is None:
        return Response(status_code=204)
    return JSONResponse(media.model_dump())
