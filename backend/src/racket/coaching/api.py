"""Plan HTTP routes (ST-061b; api-sprint-04 §2; FR-120..FR-123; NFR-019, NFR-051).

``/me/plan`` names no id: it is the session account's plan, so another account can never reach
it. ``POST`` checks, in order: session (401) -> Origin (403, edge middleware) -> body (422, closed
field codes) -> rate limit (429, SEC-S4-TM-01, counted after validation) -> ranking (409
``no_tagged_match``) -> assembly (409 ``no_plan_fits``) -> save; 201 with ``Location``.
``GET`` is 200 or 404 ``no_plan``.

Follow-through (ST-062; FR-124; api-sprint-04 §3): ``POST``/``DELETE
/me/plan/sessions/{session_id}/done`` and ``POST /me/plan/assignments/{assignment_id}/swap``.
Checks in order: session (401) -> Origin (403) -> ``Idempotency-Key`` or body (422) -> for the
swap, the rate limit (429, T4-PL-6 / SEC-S4-TM-01; before the id lookup, so it also caps id
probing) -> the id among the caller's own plan rows (404 ``not_found``, the same answer for
another account's, an unknown or a malformed id; NFR-051) -> the command (409 codes).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from racket.coaching.schemas import (
    PreferencesIn,
    parse_op_id,
    parse_preferences,
    parse_swap_body,
    plan_body,
    session_body,
)
from racket.coaching.service import DoneState, PlanService, library_dir, load_library
from racket.platform.db import get_session
from racket.platform.errors import NotFound
from racket.platform.ratelimit import RateLimited, RateLimiter
from racket.players.api import CurrentAccount

router = APIRouter()
DbSession = Annotated[Session, Depends(get_session)]
PLAN_PATH = "/me/plan"
DONE_PATH = "/me/plan/sessions/{session_id}/done"
SWAP_PATH = "/me/plan/assignments/{assignment_id}/swap"
GENERATIONS_PER_HOUR = 30  # SEC-4 T4-PL-6 (judgment); decisions ST-061b
SWAPS_PER_HOUR = 120  # SEC-4 T4-PL-6 (judgment); decisions ST-062-part2


def _error(description: str) -> dict[str, Any]:
    return {"description": description, "content": {"application/json": {}}}


_PREFERENCES_BODY = {
    "requestBody": {
        "required": True,
        "content": {"application/json": {"schema": PreferencesIn.model_json_schema()}},
    }
}


def _spend_slot(session: Session, key: str, per_hour: int) -> None:
    """Count one hit on ``key`` (after validation); 429 ``rate_limited`` over ``per_hour``."""
    now = datetime.now(UTC)
    retry_at = RateLimiter(session, clock=lambda: now).hit(
        key, limit=per_hour, window=timedelta(hours=1)
    )
    session.commit()  # the slot counts even when the command is then refused
    if retry_at is not None:
        raise RateLimited(retry_at, now)


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
    _spend_slot(session, f"plan:generate:{account.id}", GENERATIONS_PER_HOUR)
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


def _owned_id(raw: str) -> uuid.UUID:
    """A malformed id is the 404 of an unknown one (NFR-051)."""
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise NotFound("malformed id") from None


def _done_body(state: DoneState, *, with_replayed: bool) -> dict[str, Any]:
    body: dict[str, Any] = {
        "session_id": str(state.session_id),
        "done": state.done_at is not None,
        "done_at": None
        if state.done_at is None
        else state.done_at.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "plan_version": state.plan_version,
    }
    if with_replayed:
        body["replayed"] = state.replayed
    return body


@router.post(
    DONE_PATH,
    summary="Mark a session done (idempotent by the Idempotency-Key op id)",
    responses={
        200: _error("session_id, done, done_at, plan_version, replayed"),
        401: _error("unauthenticated"),
        404: _error("not_found: not a session of the caller's plan"),
        409: _error("idempotency_key_reused or plan_conflict"),
        422: _error("validation_failed: Idempotency-Key required or invalid"),
    },
)
def mark_session_done(
    session_id: str,
    account: CurrentAccount,
    session: DbSession,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    op_id = parse_op_id(idempotency_key)
    state = _service(session).mark_done(account.id, _owned_id(session_id), op_id)
    return JSONResponse(_done_body(state, with_replayed=True))


@router.delete(
    DONE_PATH,
    summary="Undo a session's done mark",
    responses={
        200: _error("session_id, done (false), done_at (null), plan_version"),
        401: _error("unauthenticated"),
        404: _error("not_found: not a session of the caller's plan"),
        409: _error("plan_conflict"),
    },
)
def undo_session_done(session_id: str, account: CurrentAccount, session: DbSession) -> JSONResponse:
    state = _service(session).undo_done(account.id, _owned_id(session_id))
    return JSONResponse(_done_body(state, with_replayed=False))


@router.post(
    SWAP_PATH,
    summary='"Not for me": swap a drill for another that trains the same metric',
    responses={
        200: _error("plan_version and the updated session (api-sprint-04 §2.3)"),
        401: _error("unauthenticated"),
        404: _error("not_found: not an assignment of the caller's plan"),
        409: _error("no_alternative, session_done or plan_conflict; nothing changed"),
        422: _error("validation_failed: reason too_long or invalid, unknown_field"),
        429: _error("rate_limited with retry_at"),
    },
)
def swap_drill(
    assignment_id: str,
    account: CurrentAccount,
    session: DbSession,
    body: Annotated[Any, Body(include_in_schema=False)] = None,
) -> JSONResponse:
    reason = parse_swap_body(body)
    _spend_slot(session, f"plan:swap:{account.id}", SWAPS_PER_HOUR)
    result = _service(session).swap(account.id, _owned_id(assignment_id), reason)
    n, plan = result.session, result.stored.plan
    return JSONResponse(
        {
            "plan_version": plan.version,
            "session": session_body(
                result.stored.sessions[n],
                plan.sessions[n],
                result.cited.sessions[n],
                result.drill_names,
            ),
        }
    )
