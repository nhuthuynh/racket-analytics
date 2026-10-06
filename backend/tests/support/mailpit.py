"""Read sign-in emails from Mailpit (ST-013; ADR 0008 dev mail). Real service, never a mock.

``MAILPIT_API_URL`` points at the Mailpit UI/API port (Compose service ``mailpit``). Locally,
without it, tests skip with a reason; in CI (``CI=true``) a missing Mailpit is a failure.
"""

from __future__ import annotations

import os
import re
import time

import httpx
import pytest

from tests.support import contract


def api_url() -> str:
    url = os.environ.get(contract.MAILPIT_API_ENV, "").rstrip("/")
    if not url:
        if os.environ.get("CI") == "true":
            pytest.fail(f"{contract.MAILPIT_API_ENV} is not set in CI", pytrace=False)
        pytest.skip(f"needs Mailpit ({contract.MAILPIT_API_ENV}=http://127.0.0.1:8025)")
    return url


def messages_to(address: str) -> list[dict[str, object]]:
    response = httpx.get(f"{api_url()}/api/v1/search", params={"query": f'to:"{address}"'})
    response.raise_for_status()
    return list(response.json().get("messages") or [])


def text_of(message_id: str) -> str:
    response = httpx.get(f"{api_url()}/api/v1/message/{message_id}")
    response.raise_for_status()
    body = response.json()
    return f"{body.get('Text', '')}\n{body.get('HTML', '')}"


def wait_for_messages(address: str, count: int = 1, timeout_s: float = 10.0) -> list[str]:
    """Bodies of the messages to ``address``, newest first, once at least ``count`` arrived."""
    deadline = time.monotonic() + timeout_s
    while True:
        found = messages_to(address)
        if len(found) >= count or time.monotonic() > deadline:
            return [text_of(str(m["ID"])) for m in found]
        time.sleep(0.2)


def token_from(body: str) -> str:
    m = re.search(contract.SIGN_IN_LINK, body)
    assert m, "no sign-in link with a 43-character token in the email"
    return m.group("token")
