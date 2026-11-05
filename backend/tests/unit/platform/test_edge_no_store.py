"""ST-078d (NFR-067.1): ``EdgeMiddleware`` answers every GET with exactly one
``Cache-Control: no-store``, whatever the route or the error path set. Negative cases first:
a route that asks for caching, a route that sends two values, and an exception that escapes
the app. No network, disk or database (in-process ASGI app).
"""

from __future__ import annotations

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from racket.platform.errors import ErrorMapper
from racket.platform.http import EdgeMiddleware, install_error_handlers
from tests.support.no_store import cache_control


def _app() -> FastAPI:
    app = FastAPI()
    mapper = ErrorMapper()
    install_error_handlers(app, mapper)
    app.add_middleware(EdgeMiddleware, mapper=mapper)

    @app.get("/cacheable")
    def cacheable() -> JSONResponse:
        return JSONResponse({"ok": True}, headers={"Cache-Control": "public, max-age=3600"})

    @app.get("/two-values")
    def two_values() -> JSONResponse:
        response = JSONResponse({"ok": True})
        response.headers.append("Cache-Control", "private")
        response.headers.append("Cache-Control", "max-age=60")
        return response

    @app.get("/explodes")
    def explodes() -> None:
        raise RuntimeError("boom")

    @app.get("/plain")
    def plain() -> dict[str, bool]:
        return {"ok": True}

    return app


async def _get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.get(path)


async def test_a_route_that_asks_to_be_cached_still_answers_no_store() -> None:
    response = await _get("/cacheable")
    assert response.status_code == 200
    assert cache_control(response.headers) == ["no-store"]


async def test_a_route_that_sends_two_cache_values_answers_one_no_store() -> None:
    assert cache_control((await _get("/two-values")).headers) == ["no-store"]


async def test_an_escaped_exception_answers_no_store() -> None:
    response = await _get("/explodes")
    assert response.status_code == 500
    assert cache_control(response.headers) == ["no-store"]


async def test_a_missing_route_answers_no_store() -> None:
    response = await _get("/nowhere")
    assert response.status_code == 404
    assert cache_control(response.headers) == ["no-store"]


async def test_a_plain_route_answers_no_store() -> None:  # positive control
    response = await _get("/plain")
    assert response.status_code == 200
    assert cache_control(response.headers) == ["no-store"]
