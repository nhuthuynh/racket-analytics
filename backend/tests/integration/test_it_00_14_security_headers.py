"""IT-00-14 (API, ST-005; NFR-061, NFR-067): security headers are present on JSON and error
responses; authenticated JSON is not cacheable. HTML responses are checked by the web lane's
Playwright suite (web/e2e/security-headers.spec.ts) because the API serves no HTML."""

from __future__ import annotations

import httpx

from tests.support import contract
from tests.support.api import sign_in


def _assert_baseline(response: httpx.Response) -> None:
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"


async def test_health_json_has_baseline_headers(api_client: httpx.AsyncClient) -> None:
    _assert_baseline(await api_client.get("/healthz"))


async def test_error_response_has_baseline_headers(api_client: httpx.AsyncClient) -> None:
    _assert_baseline(await api_client.get("/no/such/route"))


async def test_authenticated_json_is_no_store(api_client: httpx.AsyncClient) -> None:
    await sign_in(api_client, "ivy")

    response = await api_client.get(contract.MATCHES)

    _assert_baseline(response)
    assert response.headers.get("Cache-Control") == "no-store"


async def test_server_banner_does_not_reveal_versions(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/healthz")

    assert "server" not in {k.lower() for k in response.headers} or not any(
        ch.isdigit() for ch in response.headers["server"]
    )
