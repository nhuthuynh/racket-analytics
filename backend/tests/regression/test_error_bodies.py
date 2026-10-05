"""Mandatory regression suite: error bodies (IT-00-13; testing-strategy §5; NFR-058;
AQS/SEC-04, AQS/SEC-12). Never deleted.

Every error is {"error": {"code", "message", "support_ref"}} with no stack trace, exception
type, query, module path or secret, and never echoes the request input.
"""

from __future__ import annotations

from typing import Any

import httpx

from tests.support import contract
from tests.support.api import sign_in
from tests.support.errors import BOOBY_TRAP, ExplodingService, assert_generic_error


async def test_unhandled_exception_returns_generic_500(
    app: Any, api_client: httpx.AsyncClient
) -> None:
    def boom() -> None:
        raise RuntimeError(BOOBY_TRAP)

    app.add_api_route("/__test__/boom", boom, methods=["GET"])

    assert_generic_error(await api_client.get("/__test__/boom"), 500)


async def test_failing_dependency_returns_generic_500(
    app: Any, api_client: httpx.AsyncClient
) -> None:
    await sign_in(api_client, "ivy")
    created = await api_client.post(contract.MATCHES, json={"title": "t", "format": "singles"})
    app.dependency_overrides[contract.MATCH_SERVICE_DEPENDENCY.load()] = ExplodingService

    response = await api_client.get(contract.MATCH.format(match_id=created.json()["id"]))

    assert_generic_error(response, 500)


async def test_unknown_route_returns_generic_404(api_client: httpx.AsyncClient) -> None:
    assert_generic_error(await api_client.get("/no/such/route"), 404)


async def test_wrong_method_returns_generic_405(api_client: httpx.AsyncClient) -> None:
    assert_generic_error(await api_client.delete("/healthz"), 405)


async def test_validation_error_is_generic_and_does_not_echo_input(
    api_client: httpx.AsyncClient,
) -> None:
    await sign_in(api_client, "ivy")
    secret_like = "sk_live_DO_NOT_ECHO_9f8e7d"

    response = await api_client.post(
        contract.MATCHES,
        json={"title": secret_like, "format": "not-a-format", "extra": secret_like},
    )

    assert_generic_error(response, 422)
    assert secret_like not in response.text


async def test_support_refs_are_unique_per_error(app: Any, api_client: httpx.AsyncClient) -> None:
    def boom() -> None:
        raise RuntimeError("x")

    app.add_api_route("/__test__/boom2", boom, methods=["GET"])

    first = assert_generic_error(await api_client.get("/__test__/boom2"), 500)
    second = assert_generic_error(await api_client.get("/__test__/boom2"), 500)

    assert first["support_ref"] != second["support_ref"]
