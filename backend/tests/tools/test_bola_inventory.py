"""The BOLA endpoint inventory itself works (it is the guard; it must not pass vacuously)."""

from __future__ import annotations

from fastapi import FastAPI

from tests.regression.bola import MATRIX, id_routes, uncovered_routes


def _app_with(*paths: tuple[str, str]) -> FastAPI:
    app = FastAPI()
    for method, path in paths:
        app.add_api_route(path, lambda: None, methods=[method])
    return app


def test_route_with_id_and_no_matrix_entry_is_reported_by_name() -> None:
    app = _app_with(("GET", "/matches/{match_id}/secret-new-thing"))

    assert uncovered_routes(app) == ["GET /matches/{match_id}/secret-new-thing"]


def test_routes_without_path_parameters_are_not_in_the_inventory() -> None:
    app = _app_with(("GET", "/matches"), ("POST", "/matches"), ("GET", "/healthz"))

    assert id_routes(app) == set()


def test_each_method_on_an_id_route_needs_its_own_entry() -> None:
    # PUT: a method on a probed path that has no MATRIX entry (DELETE has one since Sprint 3).
    app = _app_with(("GET", "/matches/{match_id}"), ("PUT", "/matches/{match_id}"))

    assert ("PUT", "/matches/{match_id}") not in MATRIX
    assert uncovered_routes(app) == ["PUT /matches/{match_id}"]


def test_exempt_route_is_not_reported() -> None:
    app = _app_with(("GET", "/static/{name}"))

    assert uncovered_routes(app, exempt={("GET", "/static/{name}"): "public asset"}) == []


def test_matrix_covers_the_sprint_0_id_routes() -> None:
    assert {("GET", "/matches/{match_id}"), ("GET", "/matches/{match_id}/media")} <= set(MATRIX)
