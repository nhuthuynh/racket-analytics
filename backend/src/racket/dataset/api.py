"""Full Tag HTTP routes (ST-052c; api-sprint-03 §5; FR-150, FR-151; NFR-051).

Order of checks: session (401) -> Origin on POST (403, edge middleware) -> labeller role (404)
-> owner filter (404) -> consent (409 ``no_consent``) -> video facts (409 ``match_not_ready``)
-> body (422 ``invalid_label``). A non-labeller and another account's match get exactly the
answer of an unknown match id, so neither the tool nor the match is revealed (SEC-S3-TM-08).
Label values are never echoed or logged (NFR-057).

``POST`` takes, in the global lock order (deletion-and-purge §3.1): the account row ``FOR SHARE``,
the live match row ``FOR SHARE`` (so a ``DELETE /matches/{id}`` commits before the label or after
it, never across it; a match deleted meanwhile is 404, PE-052c-R1-01), then the label session row.
"""

from __future__ import annotations

import contextlib
import logging
import math
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from racket.dataset.full_tag import (
    Access,
    FullTagSession,
    LabelRefused,
    decide_access,
)
from racket.dataset.labels import DOUBLES, SINGLES
from racket.dataset.repository import LabelRepository
from racket.matches import public as matches
from racket.platform.db import get_session
from racket.platform.errors import AppError, FieldError, NotFound, Unauthenticated, ValidationFailed
from racket.platform.logs import SECURITY_LOGGER
from racket.platform.ratelimit import RateLimited, RateLimiter
from racket.players import public as players
from racket.players.api import CurrentAccount
from racket.video_ingest.public import media_summary

router = APIRouter()
security_log = logging.getLogger(SECURITY_LOGGER)
log = logging.getLogger(__name__)
DbSession = Annotated[Session, Depends(get_session)]
NO_STORE = {"Cache-Control": "no-store"}


class LabelNotFound(NotFound):
    pass


class NoConsent(AppError):
    status, code = 409, "no_consent"


class LabelMatchNotReady(AppError):
    status, code = 409, "match_not_ready"


class InvalidLabel(ValidationFailed):
    code = "invalid_label"


def finite_json(value: object) -> bool:
    """No NaN or infinity anywhere (Python's JSON reader accepts them; JSONB does not)."""
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, Mapping):
        return all(finite_json(v) for v in value.values())
    if isinstance(value, list | tuple):
        return all(finite_json(v) for v in value)
    return True


@dataclass(frozen=True)
class LabelTarget:
    match_id: uuid.UUID
    owner_id: uuid.UUID
    fps: int
    frame_count: int
    players: tuple[str, ...]


def label_target(
    match_id: str, request: Request, account: CurrentAccount, session: DbSession
) -> LabelTarget:
    parsed = None
    with contextlib.suppress(ValueError):
        parsed = uuid.UUID(match_id)
    fmt = None
    if parsed is not None and players.has_role(session, account.id, "labeller"):
        fmt = matches.owned_format(session, parsed, account.id)
    if parsed is None or fmt is None:
        security_log.info(
            "access denied",
            extra={"event": "authz.denied", "account_id": str(account.id),
                   "route": getattr(request.scope.get("route"), "path", ""),
                   "method": request.method},
        )  # fmt: skip
        raise LabelNotFound("no such match for this labeller")
    consent = LabelRepository(session).consent(parsed)
    if decide_access(is_labeller=True, match_id=str(parsed), consent=consent) is Access.NO_CONSENT:
        raise NoConsent("no consent record")
    facts = media_summary(session, parsed).facts
    if facts is None or facts.vfr or facts.fps <= 0 or facts.fps != int(facts.fps):
        raise LabelMatchNotReady("no probed constant-frame-rate video")
    fps = int(facts.fps)
    return LabelTarget(
        parsed,
        account.id,
        fps,
        facts.duration_ms * fps // 1000,
        DOUBLES if fmt == "doubles" else SINGLES,
    )


Target = Annotated[LabelTarget, Depends(label_target)]


def _session_of(target: LabelTarget, row: Any) -> FullTagSession:
    return FullTagSession(
        clip=f"match:{target.match_id}",
        fps=target.fps,
        frame_count=target.frame_count,
        players=target.players,
        rallies=tuple(row.rallies) if row is not None else (),
        events=tuple(row.events) if row is not None else (),
    )


@router.get("/label/matches/{match_id}")
def open_label_session(target: Target, session: DbSession) -> JSONResponse:
    row = LabelRepository(session).load(target.match_id)
    body = {
        "match_id": str(target.match_id),
        "fps": target.fps,
        "frame_count": target.frame_count,
        "players": list(target.players),
        "version": 0 if row is None else row.version,
        "document": _session_of(target, row).export(),
    }
    return JSONResponse(body, headers=NO_STORE)


@router.post("/label/matches/{match_id}/events", status_code=201)
def add_label(
    target: Target,
    request: Request,
    session: DbSession,
    body: Annotated[Any, Body()] = None,
) -> JSONResponse:
    """One rally, hit or bounce label (gold-label-schema §4); nothing is stored on a refusal."""
    now = datetime.now(UTC)
    try:
        if not finite_json(body):
            raise InvalidLabel("not finite", [FieldError(None, "invalid")])
        if not players.lock_live_account(session, target.owner_id):  # SEC-S3-TM-05
            raise Unauthenticated("the account was deleted")
        if not matches.lock_live_match(session, target.match_id):  # held to the commit
            raise LabelNotFound("the match was deleted")
        settings = request.app.state.settings
        retry_at = RateLimiter(session, clock=lambda: now).hit(
            f"label:command:{target.owner_id}",
            limit=settings.scorebook_command_limit_per_minute,
            window=timedelta(minutes=1),
        )
        if retry_at is not None:
            raise RateLimited(retry_at, now)
        repo = LabelRepository(session)
        row = repo.lock_or_create(target.match_id, target.owner_id, now)
        try:
            after = _session_of(target, row).add(body)
        except LabelRefused as refused:  # api-sprint-03 §5.4: one entry per problem, no values
            fields = [FieldError(p.field, p.code) for p in refused.problems]
            raise InvalidLabel("label refused", fields) from None
        version = int(row.version) + 1
        repo.save(target.match_id, version, list(after.rallies), list(after.events), now)
        session.commit()
    except BaseException:
        session.rollback()
        raise
    log.info(
        "label added",
        extra={"event": "label.added", "match_id": str(target.match_id), "version": version},
    )
    return JSONResponse(
        {"version": version, "rallies": len(after.rallies), "events": len(after.events)},
        status_code=201,
        headers=NO_STORE,
    )


@router.get("/label/matches/{match_id}/export")
def export_labels(target: Target, session: DbSession) -> JSONResponse:
    row = LabelRepository(session).load(target.match_id)
    headers = {
        **NO_STORE,
        "Content-Disposition": f'attachment; filename="labels-{target.match_id}.json"',
    }
    return JSONResponse(_session_of(target, row).export(), headers=headers)
