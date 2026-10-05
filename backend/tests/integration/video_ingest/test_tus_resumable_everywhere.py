"""R3-04 / QA-R3-10 (routed by ADR 0022; sprint-01 decision-log 2026-10-05): every response on
a tus path carries ``Tus-Resumable: 1.0.0``, including 405 from the router and the global 500
fallback. Positive control: a non-tus route does not get the header."""

from __future__ import annotations

import uuid
from typing import Any

import httpx

from racket.video_ingest.api import get_upload_service
from tests.support.api import sign_in
from tests.support.errors import ExplodingService

ID = str(uuid.uuid4())


async def test_405_on_an_upload_resource_has_tus_resumable(api_client: httpx.AsyncClient) -> None:
    for method in ("DELETE", "GET", "PUT"):
        response = await api_client.request(method, f"/uploads/{ID}")
        assert response.status_code == 405, method
        assert response.headers.get("tus-resumable") == "1.0.0", method


async def test_405_on_the_creation_path_has_tus_resumable(api_client: httpx.AsyncClient) -> None:
    response = await api_client.delete(f"/matches/{ID}/uploads")
    assert response.status_code == 405
    assert response.headers.get("tus-resumable") == "1.0.0"


async def test_a_500_on_a_tus_path_has_tus_resumable(
    app: Any, api_client: httpx.AsyncClient
) -> None:
    await sign_in(api_client, "ivy")
    app.dependency_overrides[get_upload_service] = ExplodingService
    response = await api_client.head(f"/uploads/{ID}", headers={"Tus-Resumable": "1.0.0"})
    assert response.status_code == 500
    assert response.headers.get("tus-resumable") == "1.0.0"


async def test_other_routes_do_not_get_the_header(api_client: httpx.AsyncClient) -> None:
    response = await api_client.delete("/healthz")
    assert response.status_code == 405
    assert "tus-resumable" not in response.headers
    assert "tus-resumable" not in (await api_client.get("/uploadsx")).headers
