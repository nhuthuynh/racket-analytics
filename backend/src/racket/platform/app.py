"""The API application factory (ST-005; ADR 0012 seam ``create_app``).

``create_app()`` reads ``Settings`` from the environment and refuses to build on bad
configuration (``ConfigurationError``). ``racket.platform.app:app`` (the uvicorn target used by
``infra/docker/backend.Dockerfile``) is built lazily on first access, so importing this module
never reads the environment.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import cache
from typing import Any

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from racket.platform.db import engine_for, session_factory, upgrade_to_head
from racket.platform.errors import ErrorMapper
from racket.platform.health import router as health_router
from racket.platform.http import EdgeMiddleware, install_error_handlers
from racket.platform.logs import configure_logging
from racket.platform.settings import Settings
from racket.platform.slis import HttpMetricsMiddleware, configure_metrics
from racket.platform.storage import ObjectStore
from racket.platform.tracing import configure_tracing

log = logging.getLogger("racket.platform")


def _startup(app: FastAPI) -> None:
    settings: Settings = app.state.settings
    log.info(
        "starting api", extra={"event": "app.start", "settings": settings.redacted()}
    )  # secrets redacted [EP/ENG-20]
    if settings.app_env == "dev":
        upgrade_to_head(settings.database_url)  # dev convenience; CI and prod migrate as a step
    if settings.dev_identity_enabled and settings.app_env in ("dev", "test"):
        from racket.players.service import IdentityService

        with app.state.session_factory() as session:
            IdentityService(session).seed_dev_users()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level)
    configure_tracing("racket-api", settings.otel_exporter_otlp_endpoint)
    configure_metrics("racket-api", settings.otel_exporter_otlp_metrics_endpoint)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await run_in_threadpool(_startup, app)
        yield
        log.info("stopping api", extra={"event": "app.stop"})

    public_docs = settings.app_env in ("dev", "test")
    app = FastAPI(
        title="racket-analytics API",
        lifespan=lifespan,
        docs_url="/docs" if public_docs else None,
        redoc_url="/redoc" if public_docs else None,
        openapi_url="/openapi.json" if public_docs else None,
    )
    app.state.settings = settings
    app.state.session_factory = session_factory(engine_for(settings.database_url))
    app.state.object_store = cache(lambda: ObjectStore.from_settings(settings))

    mapper = ErrorMapper()
    install_error_handlers(app, mapper)
    app.add_middleware(EdgeMiddleware, mapper=mapper, allowed_origins=settings.allowed_origins)
    app.add_middleware(HttpMetricsMiddleware)  # outermost: NFR-041 availability SLI (ST-024)

    from racket.matches.api import router as matches_router
    from racket.players.api import dev_router
    from racket.players.api import router as players_router
    from racket.video_ingest.api import router as uploads_router

    app.include_router(health_router)
    app.include_router(players_router)
    if settings.dev_identity_enabled:
        app.include_router(dev_router)  # the /dev/* routes exist only when enabled (api §2)
    app.include_router(matches_router)
    app.include_router(uploads_router)
    return app


def __getattr__(name: str) -> Any:
    """``racket.platform.app:app`` for uvicorn, built on first access."""
    if name == "app":
        return _default_app()
    raise AttributeError(name)


@cache
def _default_app() -> FastAPI:
    return create_app()
