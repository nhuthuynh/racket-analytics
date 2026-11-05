"""ST-075d: the API 5xx value on the ADR 0012 fault seam (NFR-041.5 fault path, NFR-041.6;
threat note T5-OB-5; AQS/SEC-12).

``RACKET_FAULT_INJECTION=api:5xx_on_header`` turns a request carrying ``X-Racket-Fault: 5xx``
into the generic 500 before routing. ``Settings.from_env`` keeps the seam only under
``APP_ENV=test``, so the middleware is inert elsewhere. The fault middleware sits inside
``HttpMetricsMiddleware``, so every injected 500 reaches the availability SLI
(PE-PLAN05-R2-03). Negative cases first. No network, disk or database.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from racket.platform.app import create_app
from racket.platform.fault import API_5XX_ON_HEADER, FaultMiddleware
from racket.platform.settings import Settings
from racket.platform.slis import HttpMetricsMiddleware
from tests.support.errors import assert_generic_error

BASE = {
    "DATABASE_URL": "postgresql://u:p@127.0.0.1:5432/db",
    "S3_BUCKET_MEDIA": "media",
    # required under staging and prod
    "ALLOWED_ORIGINS": "https://app.example.test",
    "PUBLIC_WEB_ORIGIN": "https://app.example.test",
    "AUTH_EMAIL_KEY": "unit-test-email-key-0123456789abcdef",
}
FAULT_HEADER = {"X-Racket-Fault": "5xx"}


def settings(app_env: str, seam: str | None) -> Settings:
    env = {**BASE, "APP_ENV": app_env}
    if seam is not None:
        env["RACKET_FAULT_INJECTION"] = seam
    return Settings.from_env(env)


async def ok_app(scope: Any, receive: Any, send: Any) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


async def get(app: Any, headers: dict[str, str] | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.get("/healthz", headers=headers or {})


def fault_is_inside_metrics(app: FastAPI) -> bool:
    """Starlette lists user middleware outermost first."""
    order = [m.cls for m in app.user_middleware]
    if HttpMetricsMiddleware not in order or FaultMiddleware not in order:
        return False
    return order.index(HttpMetricsMiddleware) < order.index(FaultMiddleware)


# ---------------------------------------------------------------- negative cases first
@pytest.mark.parametrize("app_env", ["dev", "staging", "prod"])
async def test_the_seam_set_outside_app_env_test_ignores_the_header(app_env: str) -> None:
    middleware = FaultMiddleware(ok_app, settings=settings(app_env, API_5XX_ON_HEADER))

    response = await get(middleware, FAULT_HEADER)

    assert response.status_code == 200


async def test_the_header_without_the_seam_is_a_normal_response() -> None:
    middleware = FaultMiddleware(ok_app, settings=settings("test", None))

    assert (await get(middleware, FAULT_HEADER)).status_code == 200


@pytest.mark.parametrize("seam", ["probe:sleep=60", "probe:fail_after_partial_write", "api:5xx"])
async def test_another_seam_value_ignores_the_header(seam: str) -> None:
    middleware = FaultMiddleware(ok_app, settings=settings("test", seam))

    assert (await get(middleware, FAULT_HEADER)).status_code == 200


@pytest.mark.parametrize("value", ["", "4xx", "500", "5XX "])
async def test_another_header_value_is_a_normal_response(value: str) -> None:
    middleware = FaultMiddleware(ok_app, settings=settings("test", API_5XX_ON_HEADER))

    assert (await get(middleware, {"X-Racket-Fault": value})).status_code == 200


async def test_the_seam_without_the_header_is_a_normal_response() -> None:
    middleware = FaultMiddleware(ok_app, settings=settings("test", API_5XX_ON_HEADER))

    assert (await get(middleware)).status_code == 200


def test_a_fault_middleware_added_last_is_outside_the_metrics_and_fails_the_check() -> None:
    app = FastAPI()
    app.add_middleware(HttpMetricsMiddleware)
    app.add_middleware(FaultMiddleware, settings=settings("test", API_5XX_ON_HEADER))

    assert not fault_is_inside_metrics(app)


# ---------------------------------------------------------------- the fault path
async def test_the_seam_and_the_header_give_the_generic_500_before_routing() -> None:
    reached: list[str] = []

    async def app(scope: Any, receive: Any, send: Any) -> None:
        reached.append(scope["path"])
        await ok_app(scope, receive, send)

    middleware = FaultMiddleware(app, settings=settings("test", API_5XX_ON_HEADER))

    response = await get(middleware, FAULT_HEADER)

    assert_generic_error(response, 500)
    assert reached == []


def test_create_app_registers_the_fault_middleware_inside_the_metrics_middleware() -> None:
    app = create_app(settings("test", API_5XX_ON_HEADER))

    assert app.user_middleware[0].cls is HttpMetricsMiddleware
    assert fault_is_inside_metrics(app)
