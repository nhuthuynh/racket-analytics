"""Liveness and readiness (ST-005; api-sprint-00 §4)."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from racket.platform.db import get_session

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(request: Request, session: Annotated[Session, Depends(get_session)]) -> JSONResponse:
    checks: dict[str, str] = {}

    def check(name: str, probe: Any) -> None:
        try:
            probe()
            checks[name] = "ok"
        except Exception as exc:  # noqa: BLE001 - readiness names the dependency and nothing more
            log.warning(
                "readiness check failed", extra={"check": name, "exc_type": type(exc).__name__}
            )
            checks[name] = "fail"

    check("database", lambda: session.execute(text("SELECT 1")))
    check("object_store", lambda: request.app.state.object_store().ping())
    check("queue", lambda: session.execute(text("SELECT 1 FROM jobs LIMIT 1")))
    ready = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ready" if ready else "not_ready", "checks": checks},
        status_code=200 if ready else 503,
    )
