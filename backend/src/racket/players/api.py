"""Identity HTTP routes and the ``current_account`` dependency (ST-006; context map R1 OHS).

Authentication is an opaque session cookie (api-sprint-00 §2). ``current_account`` runs before
any resource lookup, so a 401 reveals nothing about whether a resource exists.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from racket.platform.db import get_session
from racket.platform.errors import AppError, ErrorMapper, NotFound, Unauthenticated
from racket.platform.logs import SECURITY_LOGGER, user_id_var
from racket.platform.settings import Settings
from racket.players.domain import AgeGate, client_ip, under_age_message
from racket.players.service import (
    Account,
    AccountDeletion,
    AgeConfirmation,
    IdentityService,
    MagicLinkService,
)

security_log = logging.getLogger(SECURITY_LOGGER)

SECURE_COOKIE = "__Host-racket_session"
TEST_COOKIE = "racket_session"

router = APIRouter()
dev_router = APIRouter(prefix="/dev")


def settings_of(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def cookie_name(settings: Settings) -> str:
    return SECURE_COOKIE if settings.secure_cookies else TEST_COOKIE


def presented_token(request: Request) -> str | None:
    return request.cookies.get(cookie_name(settings_of(request))) or None


class AgeConfirmationRequired(AppError):
    """FR-003: a pending sign-in or an unconfirmed account, while the age gate is on."""

    status, code = 403, "age_confirmation_required"


class UnderAge(AppError):
    status, code = 403, "under_age"


def _holder(request: Request, session: Session) -> Account | str | None:
    """The session's account, else the token of a live pending sign-in, else ``None``."""
    token = presented_token(request)
    if not token:
        return None
    identity = IdentityService(session, settings_of(request))
    account = identity.account_for_token(token)
    if account is None and settings_of(request).feature_age_gate and identity.is_pending(token):
        return token
    return account


async def current_account(
    request: Request, session: Annotated[Session, Depends(get_session)]
) -> Account:
    """401 unless the request carries a valid session; with the age gate on, 403 until the
    holder confirmed being an adult (deny by default, SEC-4 T4-AG-2). Sets the pseudonymous
    log user_id."""
    holder = await run_in_threadpool(_holder, request, session)
    if holder is None:
        raise Unauthenticated("no valid session")
    if isinstance(holder, str):
        raise AgeConfirmationRequired("pending sign-in")
    account = holder
    if not AgeGate(settings_of(request).feature_age_gate).admits(account.age_confirmed_at):
        raise AgeConfirmationRequired("age not confirmed")
    # Set in the request task's context, so every later log line of this request carries it.
    user_id_var.set(str(account.id))
    return account


CurrentAccount = Annotated[Account, Depends(current_account)]


class SignInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Unknown names get 401, not 422, so the schema does not reveal which users exist.
    username: str = Field(max_length=64)


class Me(BaseModel):
    id: str
    display_name: str | None  # null for magic-link accounts (api-sprint-01 §2.3)


class LinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Any JSON value; the address rules (and the ``email_invalid`` code) are the domain's.
    email: object


class ExchangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class ExchangedAccount(BaseModel):
    id: str
    display_name: str | None


class ExchangeResponse(BaseModel):
    account: ExchangedAccount | None  # null: a pending sign-in (age gate on, api-sprint-04 §4)
    new_account: bool


def request_ip(request: Request) -> str:
    settings = settings_of(request)
    peer = request.client.host if request.client else None
    return client_ip(request.headers.get("x-forwarded-for"), peer, settings.trusted_proxy_hops)


def set_session_cookie(response: Response, settings: Settings, token: str, max_age: int) -> None:
    response.set_cookie(
        cookie_name(settings),
        token,
        max_age=max_age,
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="lax",
    )


@router.post("/auth/links", status_code=202)
def request_link(
    body: LinkRequest, request: Request, session: Annotated[Session, Depends(get_session)]
) -> Response:
    """202 for every well-formed address, known or not (T-ML-6); the email is a queued job."""
    MagicLinkService(session, settings_of(request)).request_link(body.email, request_ip(request))
    return Response(status_code=202)


@router.post("/auth/exchange")
def exchange_link(
    body: ExchangeRequest,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> ExchangeResponse:
    """A valid, unused, unexpired link becomes a new session cookie (api-sprint-01 §2.2)."""
    settings = settings_of(request)
    result = MagicLinkService(session, settings).exchange(
        body.token, request_ip(request), presented_token(request)
    )
    set_session_cookie(response, settings, result.session_token, settings.session_absolute_seconds)
    found = result.account
    account = (
        None
        if found is None
        else ExchangedAccount(id=str(found.id), display_name=found.display_name)
    )
    return ExchangeResponse(account=account, new_account=result.new_account)


@dev_router.get("/users")
def dev_users(session: Annotated[Session, Depends(get_session)]) -> dict[str, list[dict[str, str]]]:
    return {"items": IdentityService(session).dev_users()}


@dev_router.post("/sign-in", status_code=204)
def dev_sign_in(
    body: SignInRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    settings = settings_of(request)
    result = IdentityService(session, settings).sign_in(body.username, presented_token(request))
    if result is None:
        security_log.info("sign-in refused", extra={"event": "auth.sign_in", "outcome": "refused"})
        raise Unauthenticated("sign-in refused")
    account, token = result
    security_log.info(
        "sign-in", extra={"event": "auth.sign_in", "outcome": "ok", "account_id": str(account.id)}
    )
    response = Response(status_code=204)
    set_session_cookie(response, settings, token, 12 * 3600)
    return response


def _signed_out(response: Response, settings: Settings) -> Response:
    # The browser drops its HTTP cache; the client clears its own storage (FR-011, NFR-067).
    response.headers["Clear-Site-Data"] = '"cache"'
    response.delete_cookie(
        cookie_name(settings), path="/", secure=settings.secure_cookies, httponly=True,
        samesite="lax",
    )  # fmt: skip
    return response


@router.post("/auth/sign-out", status_code=204)
def sign_out(request: Request, session: Annotated[Session, Depends(get_session)]) -> Response:
    settings = settings_of(request)
    token = presented_token(request)
    if token:
        IdentityService(session, settings).sign_out(token)
    return _signed_out(Response(status_code=204), settings)


@router.delete("/me", status_code=202)
def delete_me(
    request: Request,
    account: CurrentAccount,
    session: Annotated[Session, Depends(get_session)],
    body: Annotated[Any, Body()] = None,
) -> Response:
    """FR-007 (api-sprint-03 §4.2): every match deleted, every session ended, the address
    freed; signed out here with the ``POST /auth/sign-out`` headers. 202: the purge follows."""
    tombstone = AccountDeletion(session).delete(account.id, body)
    response = JSONResponse(
        tombstone.response(), status_code=202, headers={"Cache-Control": "no-store"}
    )
    return _signed_out(response, settings_of(request))


@router.get("/me")
def me(account: CurrentAccount) -> Me:
    return Me(id=str(account.id), display_name=account.display_name)


class ConfirmedMe(Me):
    age_confirmed_at: str


@router.post("/me/age-confirmation")
def confirm_age(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    body: Annotated[Any, Body()] = None,
) -> Response:
    """FR-003 (api-sprint-04 §4): 404 while ``FEATURE_AGE_GATE`` is off; 401 without a session
    or pending sign-in; ``true`` -> 200 ``GET /me`` plus ``age_confirmed_at``; ``false`` -> 403
    ``under_age``, signed out, no account row."""
    settings = settings_of(request)
    if not settings.feature_age_gate:
        raise NotFound("age gate off")
    holder = _holder(request, session)
    if holder is None:
        raise Unauthenticated("no valid session")
    service = AgeConfirmation(session, settings)
    if isinstance(holder, str):
        confirmed = service.answer_pending(holder, body)
        account = confirmed and confirmed[0]
    else:
        account = service.answer_account(holder, body)
    if account is None:
        error = ErrorMapper().map(UnderAge("under age"))
        payload = error.body()
        payload["error"]["message"] = under_age_message(settings.age_minimum)
        refused = JSONResponse(payload, status_code=403, headers={"Cache-Control": "no-store"})
        return _signed_out(refused, settings)
    user_id_var.set(str(account.id))
    confirmed_at = account.age_confirmed_at or datetime.now(UTC)  # always set by the answer
    at = confirmed_at.astimezone(UTC).isoformat(timespec="seconds")
    me = ConfirmedMe(
        id=str(account.id), display_name=account.display_name,
        age_confirmed_at=at.replace("+00:00", "Z"),
    )  # fmt: skip
    response = JSONResponse(me.model_dump(), headers={"Cache-Control": "no-store"})
    if isinstance(holder, str) and confirmed:
        set_session_cookie(response, settings, confirmed[1], settings.session_absolute_seconds)
    return response
