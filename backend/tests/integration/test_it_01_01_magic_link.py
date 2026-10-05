"""IT-01-01..IT-01-03 (ST-013; FR-001; NFR-023, NFR-055, NFR-057; ADR 0025) and the ST-013
threat-model controls T-ML-1/2/3/6/7/8/9/10/14 (docs/security/threat-model-sprint-01.md, which
makes them acceptance criteria, ADR 0022 rule 4).

API <-> worker <-> Mailpit <-> DB, all real (AQS/OPS-05). Written before ST-013: RED until it
lands. Tests that read email need Mailpit (``MAILPIT_API_URL``; skip locally, fail in CI).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from typing import Any

import pytest

from tests.support import auth, contract, mailpit
from tests.support.api import ApiDriver
from tests.support.logscan import scan

pytestmark = [pytest.mark.red_until(story="ST-013"), pytest.mark.slow]

WEB_ORIGIN = "https://app.racket.test"


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set before the app is built (autouse fixtures run before ``api``)."""
    monkeypatch.setenv("PUBLIC_WEB_ORIGIN", WEB_ORIGIN)
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "0")


def _signed_in(api: ApiDriver) -> tuple[Any, str, str]:
    client = auth.new_client(api)
    email = auth.unique_email()
    assert auth.request_link(api, client, email).status_code == 202
    auth.deliver_mail()
    token = auth.link_token(api, email)
    response = auth.exchange(api, client, token)
    assert response.status_code == 200, response.text
    return client, email, token


# ------------------------------------------------------------------ IT-01-01, T-ML-2, T-ML-14
def test_it_01_01_link_signs_in_once_and_reuse_fails(api: ApiDriver) -> None:
    client, _, token = _signed_in(api)
    try:
        assert contract.SESSION_COOKIE_TEST in client.cookies
        me = api.run(client.get(contract.ME))
        assert me.status_code == 200
        assert set(me.json()) == {"id", "display_name"}  # never the email (T-ML-14)

        again = auth.exchange(api, auth.new_client(api), token)
        assert again.status_code == 401
        assert again.json()["error"]["code"] == "link_expired"
    finally:
        api.run(client.aclose())


def test_first_exchange_reports_a_new_account_and_later_ones_do_not(api: ApiDriver) -> None:
    client = auth.new_client(api)
    email = auth.unique_email()
    try:
        bodies = []
        for n in (1, 2):
            assert auth.request_link(api, client, email).status_code == 202
            auth.deliver_mail()
            bodies.append(auth.exchange(api, client, auth.link_token(api, email, n)).json())
        assert [b["new_account"] for b in bodies] == [True, False]
        assert bodies[0]["account"]["id"] == bodies[1]["account"]["id"]
    finally:
        api.run(client.aclose())


def test_link_points_at_the_configured_origin_not_the_host_header(api: ApiDriver) -> None:
    """T-ML-7: link poisoning via Host."""
    client = auth.new_client(api)
    email = auth.unique_email()
    try:
        response = api.run(
            client.post(
                contract.AUTH_LINKS, json={"email": email}, headers={"Host": "evil.example"}
            )
        )
        assert response.status_code == 202
        auth.deliver_mail()
        body = mailpit.wait_for_messages(email)[0]
        assert f"{WEB_ORIGIN}/auth/callback#token=" in body
        assert "evil.example" not in body
    finally:
        api.run(client.aclose())


def test_two_concurrent_exchanges_of_one_link_give_one_session(api: ApiDriver) -> None:
    """T-ML-3: the conditional update lets exactly one exchange win."""
    client = auth.new_client(api)
    email = auth.unique_email()
    assert auth.request_link(api, client, email).status_code == 202
    auth.deliver_mail()
    token = auth.link_token(api, email)
    a, b = auth.new_client(api), auth.new_client(api)

    async def both() -> list[int]:
        responses = await asyncio.gather(
            a.post(contract.AUTH_EXCHANGE, json={"token": token}),
            b.post(contract.AUTH_EXCHANGE, json={"token": token}),
        )
        return sorted(r.status_code for r in responses)

    try:
        assert api.run(both()) == [200, 401]
    finally:
        for c in (client, a, b):
            api.run(c.aclose())


def test_exchange_replaces_a_session_already_presented(api: ApiDriver) -> None:
    """T-ML-10 (ASVS 7.2.4): no session fixation."""
    client, email, _ = _signed_in(api)
    try:
        old = client.cookies[contract.SESSION_COOKIE_TEST]
        assert auth.request_link(api, client, email).status_code == 202
        auth.deliver_mail()
        assert auth.exchange(api, client, auth.link_token(api, email, 2)).status_code == 200
        assert client.cookies[contract.SESSION_COOKIE_TEST] != old
        stale = auth.new_client(api)
        stale.cookies.set(contract.SESSION_COOKIE_TEST, old)
        assert api.run(stale.get(contract.ME)).status_code == 401
        api.run(stale.aclose())
    finally:
        api.run(client.aclose())


# ------------------------------------------------------------------ T-ML-6 (no oracle)
def _comparable(response: Any) -> tuple[int, bytes, list[str]]:
    varying = {"date", "x-request-id", "traceparent", "server-timing", "content-length"}
    keys = sorted(k for k in response.headers if k.lower() not in varying)
    return response.status_code, response.content, keys


def test_known_and_unknown_addresses_get_identical_responses(api: ApiDriver) -> None:
    client, known, _ = _signed_in(api)
    try:
        unknown = auth.unique_email("new")
        a = auth.request_link(api, client, known)
        b = auth.request_link(api, client, unknown)
        assert _comparable(a) == _comparable(b)
        assert a.status_code == 202
    finally:
        api.run(client.aclose())


# ------------------------------------------------------------------ IT-01-02, T-ML-1, T-ML-8
def test_it_01_02_sixth_link_in_ten_minutes_is_rate_limited_with_a_retry_time(
    api: ApiDriver,
) -> None:
    client = auth.new_client(api)
    email = auth.unique_email()
    try:
        statuses = [auth.request_link(api, client, email).status_code for _ in range(5)]
        assert statuses == [202] * 5
        limited = auth.request_link(api, client, email)
        assert limited.status_code == 429
        error = limited.json()["error"]
        assert error["code"] == "rate_limited"
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z", error["retry_at"])
        assert int(limited.headers["Retry-After"]) > 0
    finally:
        api.run(client.aclose())


def test_spoofed_forwarded_for_does_not_reset_the_ip_limit(api: ApiDriver) -> None:
    client = auth.new_client(api)
    try:
        statuses = [
            api.run(
                client.post(
                    contract.AUTH_LINKS,
                    json={"email": auth.unique_email()},
                    headers={"X-Forwarded-For": f"203.0.113.{n}"},
                )
            ).status_code
            for n in range(21)
        ]
        assert statuses[:20] == [202] * 20
        assert statuses[20] == 429
    finally:
        api.run(client.aclose())


def test_guessing_tokens_is_rate_limited(api: ApiDriver) -> None:
    client = auth.new_client(api)
    try:
        statuses = [
            auth.exchange(api, client, uuid.uuid4().hex + uuid.uuid4().hex[:11]).status_code
            for _ in range(31)
        ]
        assert set(statuses[:30]) == {401}
        assert statuses[30] == 429
    finally:
        api.run(client.aclose())


# ------------------------------------------------------------------ IT-01-03, T-ML-9
def test_it_01_03_auth_log_lines_are_attributable_and_hold_no_address_or_token(
    api: ApiDriver, caplog: pytest.LogCaptureFixture, capfd: pytest.CaptureFixture[str]
) -> None:
    with caplog.at_level(logging.DEBUG):
        client, email, token = _signed_in(api)
        auth.exchange(api, client, token)  # a refused attempt
        api.run(client.aclose())
    out, err = capfd.readouterr()
    lines = out.splitlines() + err.splitlines()
    lines += [json.dumps(r.__dict__, default=str) for r in caplog.records]
    events = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    auth_events = [e for e in events if str(e.get("event", "")).startswith("auth.")]

    assert {e["event"] for e in auth_events} >= {
        "auth.link_requested",
        "auth.exchanged",
        "auth.refused",
    }
    for event in auth_events:
        assert str(event["time"]).endswith(("Z", "+00:00")), event
        assert event.get("request_id"), event
        assert event.get("account_id") or event.get("email_key"), event
    joined = "\n".join(lines)
    assert email not in joined
    assert token not in joined
    assert scan(lines) == []
