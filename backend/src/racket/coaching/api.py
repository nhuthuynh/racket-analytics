"""Plan HTTP routes (ST-061b; api-sprint-04 §2; FR-120..FR-123; NFR-019, NFR-051).

``/me/plan`` names no id: it is the session account's plan, so another account can never reach
it. ``POST`` checks, in order: session (401) -> Origin (403, edge middleware) -> body (422, closed
field codes) -> rate limit (429, SEC-S4-TM-01, counted after validation) -> ranking (409
``no_tagged_match``) -> assembly (409 ``no_plan_fits``) -> save; 201 with ``Location``.
``GET`` is 200 or 404 ``no_plan``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from racket.coaching.schemas import PreferencesIn, parse_preferences, plan_body
from racket.coaching.service import PlanService, library_dir, load_library
from racket.platform.db import get_session
from racket.platform.ratelimit import RateLimited, RateLimiter
from racket.players.api import CurrentAccount

router = APIRouter()
DbSession = Annotated[Session, Depends(get_session)]
PLAN_PATH = "/me/plan"
GENERATIONS_PER_HOUR = 30  # SEC-4 T4-PL-6 (judgment); decisions ST-061b


def _error(description: str) -> dict[str, Any]:
    return {"description": description, "content": {"application/json": {}}}


_PREFERENCES_BODY = {
    "requestBody": {
        "required": True,
        "content": {"application/json": {"schema": PreferencesIn.model_json_schema()}},
    }
}


def _service(session: Session) -> PlanService:
    return PlanService(session, load_library(library_dir()))


@router.post(
    PLAN_PATH,
    status_code=201,
    summary="Generate (or replace) the current rules-only plan",
    openapi_extra=_PREFERENCES_BODY,
    responses={
        201: _error("The plan (api-sprint-04 §2.3); Location: /me/plan"),
        401: _error("unauthenticated"),
        409: _error("no_tagged_match, no_plan_fits or plan_conflict; nothing written"),
        422: _error("validation_failed with closed field codes"),
        429: _error("rate_limited with retry_at"),
    },
)
def generate_plan(
    account: CurrentAccount,
    session: DbSession,
    body: Annotated[Any, Body(include_in_schema=False)] = None,
) -> JSONResponse:
    prefs = parse_preferences(body)
    now = datetime.now(UTC)
    retry_at = RateLimiter(session, clock=lambda: now).hit(
        f"plan:generate:{account.id}", limit=GENERATIONS_PER_HOUR, window=timedelta(hours=1)
    )
    session.commit()  # the slot counts even when the generation is refused
    if retry_at is not None:
        raise RateLimited(retry_at, now)
    view = _service(session).generate(account.id, prefs)
    return JSONResponse(plan_body(view), status_code=201, headers={"Location": PLAN_PATH})


@router.get(
    PLAN_PATH,
    summary="Read the current plan",
    responses={
        200: _error("The plan (api-sprint-04 §2.3)"),
        401: _error("unauthenticated"),
        404: _error("no_plan"),
    },
)
def get_plan(account: CurrentAccount, session: DbSession) -> JSONResponse:
    return JSONResponse(plan_body(_service(session).current(account.id)))
