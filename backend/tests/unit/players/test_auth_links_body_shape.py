"""C-09 (QA-R3-TEST-01): regression for the ``POST /auth/links`` body shape. An unknown key or
a body that is not a JSON object is a 422 that names no field and echoes nothing, and nothing
is queued. No database: the body is refused before the service runs (the app is built with a
DSN it never connects to)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from racket.platform.app import create_app

pytestmark = pytest.mark.unit
ENV = {
    "APP_ENV": "test",
    "DATABASE_URL": "postgresql://u:p@127.0.0.1:1/none",
    "S3_BUCKET_MEDIA": "b",
}


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> Any:
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    return create_app()


@pytest.mark.parametrize(
    "content",
    [
        b'{"email": "ivy@example.com", "is_admin": true}',
        b'["ivy@example.com"]',
        b'"ivy@example.com"',
        b"null",
        b"42",
    ],
)
async def test_an_unknown_key_or_a_non_object_body_is_a_422_that_echoes_nothing(
    app: Any, content: bytes
) -> None:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/auth/links", content=content,
                           headers={"content-type": "application/json"})  # fmt: skip
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert "is_admin" not in response.text
    assert "ivy@example.com" not in response.text
