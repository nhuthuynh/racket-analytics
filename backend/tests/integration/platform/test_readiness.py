"""Readiness names each dependency (ST-005; api-sprint-00 §4). Real Postgres and object store."""

from __future__ import annotations

import dataclasses
from typing import Any

import httpx

from racket.platform.app import create_app
from racket.platform.db import get_session
from racket.platform.settings import Settings
from tests.support.api import async_client


async def test_ready_when_database_store_and_queue_answer(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "object_store": "ok", "queue": "ok"},
    }


async def test_not_ready_names_only_the_failing_dependency(db_session: Any) -> None:
    settings = dataclasses.replace(Settings.from_env(), s3_endpoint_url="http://127.0.0.1:9")
    application = create_app(settings)
    application.dependency_overrides[get_session] = lambda: db_session

    async with async_client(application) as client:
        response = await client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "ok", "object_store": "fail", "queue": "ok"},
    }


async def test_dev_routes_do_not_exist_when_the_dev_provider_is_off(db_session: Any) -> None:
    settings = dataclasses.replace(Settings.from_env(), dev_identity_enabled=False)
    application = create_app(settings)

    async with async_client(application) as client:
        response = await client.post("/dev/sign-in", json={"username": "ivy"})

    assert response.status_code == 404


async def test_foreign_origin_cannot_change_state(db_session: Any) -> None:
    settings = dataclasses.replace(Settings.from_env(), allowed_origins=("https://app.example",))
    application = create_app(settings)
    application.dependency_overrides[get_session] = lambda: db_session

    async with async_client(application) as client:
        refused = await client.post(
            "/dev/sign-in", json={"username": "ivy"}, headers={"Origin": "https://evil.example"}
        )
        allowed = await client.post(
            "/dev/sign-in", json={"username": "ivy"}, headers={"Origin": "https://app.example"}
        )

    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "forbidden_origin"
    assert allowed.status_code == 204


async def test_sign_in_rotates_and_sign_out_ends_the_session(api_client: httpx.AsyncClient) -> None:
    first = await api_client.post("/dev/sign-in", json={"username": "ivy"})
    me = await api_client.get("/me")
    await api_client.post("/auth/sign-out")
    after = await api_client.get("/me")
    unknown = await api_client.post("/dev/sign-in", json={"username": "mallory"})

    assert first.status_code == 204
    assert "HttpOnly" in first.headers["set-cookie"]
    assert me.status_code == 200
    assert set(me.json()) == {"id", "display_name"}
    assert after.status_code == 401
    assert unknown.status_code == 401
