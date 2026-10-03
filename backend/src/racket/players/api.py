"""Identity HTTP routes and the ``current_account`` dependency (ST-006; context map R1 OHS).

Authentication is an opaque session cookie (api-sprint-00 §2). ``current_account`` runs before
any resource lookup, so a 401 reveals nothing about whether a resource exists.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from racket.platform.db import get_session
from racket.platform.errors import Unauthenticated
from racket.platform.logs import SECURITY_LOGGER, user_id_var
from racket.platform.settings import Settings
from racket.players.service import Account, IdentityService

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


async def current_account(
    request: Request, session: Annotated[Session, Depends(get_session)]
) -> Account:
    """401 unless the request carries a valid session. Sets the pseudonymous log user_id."""
    token = presented_token(request)
    account = None
    if token:
        account = await run_in_threadpool(IdentityService(session).account_for_token, token)
    if account is None:
        raise Unauthenticated("no valid session")
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
    display_name: str


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
    result = IdentityService(session).sign_in(body.username, presented_token(request))
    if result is None:
        security_log.info("sign-in refused", extra={"event": "auth.sign_in", "outcome": "refused"})
        raise Unauthenticated("sign-in refused")
    account, token = result
    security_log.info(
        "sign-in", extra={"event": "auth.sign_in", "outcome": "ok", "account_id": str(account.id)}
    )
    response = Response(status_code=204)
    response.set_cookie(
        cookie_name(settings),
        token,
        max_age=12 * 3600,
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/auth/sign-out", status_code=204)
def sign_out(request: Request, session: Annotated[Session, Depends(get_session)]) -> Response:
    settings = settings_of(request)
    token = presented_token(request)
    if token:
        IdentityService(session).sign_out(token)
    response = Response(status_code=204)
    response.delete_cookie(
        cookie_name(settings), path="/", secure=settings.secure_cookies, httponly=True,
        samesite="lax",
    )  # fmt: skip
    return response


@router.get("/me")
def me(account: CurrentAccount) -> Me:
    return Me(id=str(account.id), display_name=account.display_name)
