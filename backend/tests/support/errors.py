"""Assertions for the generic error body (NFR-058; AQS/SEC-04)."""

from __future__ import annotations

import re
from typing import Any

import httpx

LEAK_PATTERNS = {
    "stack trace": re.compile(r"Traceback|File \"[^\"]+\", line \d+|\.py\b"),
    "exception type": re.compile(r"\b\w+(Error|Exception)\b"),
    "SQL": re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b.+\b(FROM|INTO|SET|WHERE)\b", re.I | re.S),
    "module path": re.compile(r"\bracket\.\w+|\bsqlalchemy\b|\bpsycopg\b|\bstarlette\b", re.I),
    "secret": re.compile(r"password|hunter2|secret|token=", re.I),
}
BOOBY_TRAP = (
    "psycopg.OperationalError: SELECT * FROM matches WHERE owner_id = 42 "
    "password=hunter2 at racket.matches.repository line 87"
)


class ExplodingService:
    """Stands in for a dependency that fails unexpectedly with a message full of internals."""

    def __getattr__(self, name: str) -> object:
        def explode(*args: object, **kwargs: object) -> object:
            raise RuntimeError(BOOBY_TRAP)

        return explode


def assert_generic_error(response: httpx.Response, status: int) -> dict[str, Any]:
    assert response.status_code == status, response.text[:300]
    assert response.headers.get("content-type", "").startswith("application/json")
    body = response.json()
    assert set(body) == {"error"}, body
    error: dict[str, Any] = body["error"]
    # api-sprint-01 §1.1 (TCR row 10): exactly these keys, plus `fields` on a 422 (always an
    # array of {field, code}) and `retry_at` on a 429. The set stays closed.
    expected = {"code", "message", "support_ref"}
    if status == 422:
        expected |= {"fields"}
    if status == 429:
        expected |= {"retry_at"}
    assert set(error) == expected, error
    if status == 422:
        assert isinstance(error["fields"], list), error
        for item in error["fields"]:
            assert isinstance(item, dict), item
            assert set(item) == {"field", "code"}, item
    assert error["support_ref"], "support_ref must not be empty"
    assert_no_internals(response.text)
    return error


def assert_no_internals(text: str) -> None:
    for what, pattern in LEAK_PATTERNS.items():
        match = pattern.search(text)
        assert match is None, f"response leaks {what}: {match.group(0)!r}"
