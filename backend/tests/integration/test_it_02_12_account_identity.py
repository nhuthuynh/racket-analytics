"""IT-02-12 (ST-013b; ADR 0032 red tests 1-5; NFR-057, NFR-069): account identity is the stored
normalised address, not the 64-bit ``email_key``.

API <-> worker <-> Mailpit <-> DB, all real; needs Mailpit (``MAILPIT_API_URL``; skip locally,
fail in CI). Each test builds its own application after setting the environment, because the
key is read at startup.

1. ``AUTH_EMAIL_KEY`` rotation keeps the account and its matches.
2. A forced ``email_key`` collision gives two accounts.
3. The address on ``sign_in_links`` is nulled when the link is used or refused.
4. No log line of the sign-in holds an ``@`` (an address) or the token.
5. A legacy account (``email`` NULL, matching ``email_key``) is claimed once and gets its address.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import sqlalchemy as sa

from tests.support import auth, contract
from tests.support.api import ApiDriver

pytestmark = pytest.mark.slow

KEY_1 = "it-02-12-key-one-0000000000000000000000"
KEY_2 = "it-02-12-key-two-0000000000000000000000"


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_WEB_ORIGIN", "https://app.racket.test")
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "0")
    monkeypatch.setenv("AUTH_EMAIL_KEY", KEY_1)


@pytest.fixture
def apps(committed_db: Any) -> Iterator[list[ApiDriver]]:
    """Drivers built on demand (``_app``), closed at the end."""
    made: list[ApiDriver] = []
    yield made
    for driver in made:
        driver.close()


def _app(apps: list[ApiDriver]) -> ApiDriver:
    driver = ApiDriver(contract.APP_FACTORY.load()())
    apps.append(driver)
    return driver


def _sign_in(api: ApiDriver, email: str, nth: int = 1) -> tuple[httpx.AsyncClient, str]:
    client = auth.new_client(api)
    assert auth.request_link(api, client, email).status_code == 202
    auth.deliver_mail()
    response = auth.exchange(api, client, auth.link_token(api, email, nth))
    assert response.status_code == 200, response.text
    return client, str(response.json()["account"]["id"])


def _scalar(engine: Any, sql: str, **params: Any) -> Any:
    with engine.connect() as conn:
        return conn.execute(sa.text(sql), params).scalar()


# ------------------------------------------------------------------ 1. rotation
def test_it_02_12_key_rotation_keeps_the_account_and_its_matches(
    apps: list[ApiDriver], committed_db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    email = auth.unique_email()
    first = _app(apps)
    client, account_1 = _sign_in(first, email)
    created = first.run(client.post(contract.MATCHES, json={"title": "Kept", "format": "singles"}))
    assert created.status_code == 201, created.text
    first.run(client.aclose())

    monkeypatch.setenv("AUTH_EMAIL_KEY", KEY_2)
    second = _app(apps)
    client, account_2 = _sign_in(second, email, nth=2)
    try:
        assert account_2 == account_1
        listed = second.run(client.get(contract.MATCHES)).json()["items"]
        assert [m["title"] for m in listed] == ["Kept"]
    finally:
        second.run(client.aclose())


# ------------------------------------------------------------------ 2. collision
def test_it_02_12_two_addresses_with_the_same_key_get_two_accounts(
    apps: list[ApiDriver], committed_db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import racket.players.service as service

    monkeypatch.setattr(service, "email_key", lambda secret, email: "0123456789abcdef")
    api = _app(apps)
    a, b = auth.unique_email("ivy"), auth.unique_email("carlos")
    client_a, account_a = _sign_in(api, a)
    client_b, account_b = _sign_in(api, b)
    try:
        assert account_a != account_b
        assert _scalar(committed_db, "SELECT count(DISTINCT id) FROM accounts WHERE email_key = "
                       "'0123456789abcdef'") == 2  # fmt: skip
    finally:
        api.run(client_a.aclose())
        api.run(client_b.aclose())


# ------------------------------------------------------------------ 3. address nulled
def test_it_02_12_a_used_link_keeps_no_address(apps: list[ApiDriver], committed_db: Any) -> None:
    api = _app(apps)
    email = auth.unique_email()
    client = auth.new_client(api)
    assert auth.request_link(api, client, email).status_code == 202
    auth.deliver_mail()
    token = auth.link_token(api, email)
    # Positive control: before the exchange the link carries the address.
    assert (
        _scalar(committed_db, "SELECT count(*) FROM sign_in_links WHERE email = :e", e=email) == 1
    )
    assert auth.exchange(api, client, token).status_code == 200
    assert (
        _scalar(committed_db, "SELECT count(*) FROM sign_in_links WHERE email = :e", e=email) == 0
    )
    api.run(client.aclose())


def test_it_02_12_a_refused_expired_link_keeps_no_address(
    apps: list[ApiDriver], committed_db: Any
) -> None:
    api = _app(apps)
    email = auth.unique_email()
    client = auth.new_client(api)
    assert auth.request_link(api, client, email).status_code == 202
    auth.deliver_mail()
    token = auth.link_token(api, email)
    with committed_db.begin() as conn:
        conn.execute(
            sa.text("UPDATE sign_in_links SET expires_at = :t WHERE email = :e"),
            {"t": datetime.now(UTC) - timedelta(minutes=1), "e": email},
        )
    refused = auth.exchange(api, client, token)
    assert refused.status_code == 401, refused.text
    assert refused.json()["error"]["code"] == "link_expired"
    assert (
        _scalar(committed_db, "SELECT count(*) FROM sign_in_links WHERE email = :e", e=email) == 0
    )
    api.run(client.aclose())


# ------------------------------------------------------------------ 4. logs
def test_it_02_12_no_log_line_of_a_sign_in_holds_an_address_or_the_token(
    apps: list[ApiDriver], committed_db: Any, capfd: pytest.CaptureFixture[str]
) -> None:
    api = _app(apps)
    email = auth.unique_email()
    client = auth.new_client(api)
    capfd.readouterr()
    assert auth.request_link(api, client, email).status_code == 202
    auth.deliver_mail()
    token = auth.link_token(api, email)
    assert auth.exchange(api, client, token).status_code == 200
    out, err = capfd.readouterr()
    lines = [line for line in (out + err).splitlines() if line.startswith("{")]
    assert lines, "no JSON log line captured (positive control)"
    assert any('"auth.' in line for line in lines), "the sign-in events were not logged"
    assert [line for line in lines if "@" in line] == []
    assert [line for line in lines if token in line] == []
    api.run(client.aclose())


# ------------------------------------------------------------------ 5. legacy claim
def test_it_02_12_a_legacy_account_is_claimed_once_by_its_address(
    apps: list[ApiDriver], committed_db: Any
) -> None:
    from racket.players.domain import email_key, normalise_email

    email = auth.unique_email()
    key = email_key(KEY_1.encode(), str(normalise_email(email)))
    legacy = uuid.uuid4()
    with committed_db.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO accounts (id, created_at, email_key, email) VALUES (:i, :t, :k, NULL)"
            ),
            {"i": legacy, "t": datetime.now(UTC), "k": key},
        )
    api = _app(apps)
    client, account = _sign_in(api, email)
    api.run(client.aclose())
    assert account == str(legacy)
    assert _scalar(committed_db, "SELECT email FROM accounts WHERE id = :i", i=legacy) == (
        normalise_email(email)
    )
    client, again = _sign_in(api, email, nth=2)
    api.run(client.aclose())
    assert again == str(legacy)
    assert _scalar(committed_db, "SELECT count(*) FROM accounts WHERE email_key = :k", k=key) == 1
