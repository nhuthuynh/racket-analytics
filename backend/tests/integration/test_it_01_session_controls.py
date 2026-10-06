"""Service-level session controls through the real API and database (ST-013; ADR 0025;
threat model T-ML-11; ASVS 7.1.2, 7.3.1). SEC-R3-S1-02 / SEC-R4-S1-02: the only earlier coverage
was the pure ``SessionLifetime`` predicate, so deleting the idle check or the per-account cap in
``IdentityService`` survived the whole suite.

The sign-in link is seeded straight into ``sign_in_links`` (its SHA-256 only, as the service
stores it), so these tests need no Mailpit; the exchange, the session row and ``/me`` are real.
Time passes by moving the stored ``last_seen_at`` back, never by mocking the clock.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import sqlalchemy as sa

from racket.players.domain import MagicLinkToken
from racket.players.models import sessions, sign_in_links
from tests.support import auth, contract
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.slow]

IDLE = timedelta(seconds=604_800)  # SESSION_IDLE_SECONDS default (7 days)
CAP = 10  # SESSION_MAX_PER_ACCOUNT default


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_WEB_ORIGIN", "https://app.racket.test")
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "0")
    for name in ("SESSION_IDLE_SECONDS", "SESSION_ABSOLUTE_SECONDS", "SESSION_MAX_PER_ACCOUNT"):
        monkeypatch.delenv(name, raising=False)


def _seed_link(engine: Any, email_key: str) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    with engine.begin() as conn:
        conn.execute(
            sa.insert(sign_in_links).values(
                token_sha256=MagicLinkToken.digest_of(token),
                email_key=email_key,
                created_at=now,
                expires_at=now + timedelta(minutes=15),
            )
        )
    return token


def _sign_in(api: ApiDriver, engine: Any, email_key: str) -> httpx.AsyncClient:
    client = auth.new_client(api)
    response = auth.exchange(api, client, _seed_link(engine, email_key))
    assert response.status_code == 200, response.text
    assert contract.SESSION_COOKIE_TEST in client.cookies
    return client


def _me(api: ApiDriver, client: httpx.AsyncClient) -> int:
    return api.run(client.get(contract.ME)).status_code


def _age_all_sessions(engine: Any, by: timedelta) -> None:
    with engine.begin() as conn:
        conn.execute(sa.update(sessions).values(last_seen_at=sessions.c.last_seen_at - by))


# ------------------------------------------------------------------ idle timeout (ASVS 7.3.1)
def test_a_session_idle_for_longer_than_seven_days_is_refused(
    api: ApiDriver, committed_db: Any
) -> None:
    client = _sign_in(api, committed_db, uuid.uuid4().hex)
    try:
        assert _me(api, client) == 200
        _age_all_sessions(committed_db, IDLE + timedelta(seconds=5))
        assert _me(api, client) == 401
    finally:
        api.run(client.aclose())


def test_a_session_idle_for_just_under_seven_days_still_works_and_is_touched(
    api: ApiDriver, committed_db: Any
) -> None:
    """Positive control for the idle test: same setup, the boundary not crossed."""
    client = _sign_in(api, committed_db, uuid.uuid4().hex)
    try:
        _age_all_sessions(committed_db, IDLE - timedelta(minutes=5))
        assert _me(api, client) == 200
        with committed_db.connect() as conn:
            last_seen = conn.execute(sa.select(sessions.c.last_seen_at)).scalar_one()
        assert datetime.now(UTC) - last_seen < timedelta(minutes=1)  # touched, so it slides
    finally:
        api.run(client.aclose())


# ------------------------------------------------------------------ session cap (ASVS 7.1.2)
def test_the_eleventh_sign_in_evicts_the_oldest_session(api: ApiDriver, committed_db: Any) -> None:
    key = uuid.uuid4().hex
    clients = [_sign_in(api, committed_db, key) for _ in range(CAP + 1)]
    try:
        with committed_db.connect() as conn:
            count = conn.execute(sa.select(sa.func.count()).select_from(sessions)).scalar_one()
        assert count == CAP
        assert _me(api, clients[0]) == 401  # the oldest went
        assert [_me(api, c) for c in clients[1:]] == [200] * CAP
    finally:
        for c in clients:
            api.run(c.aclose())


def test_ten_sessions_are_all_kept(api: ApiDriver, committed_db: Any) -> None:
    """Positive control for the cap test: at the cap nothing is evicted."""
    key = uuid.uuid4().hex
    clients = [_sign_in(api, committed_db, key) for _ in range(CAP)]
    try:
        assert [_me(api, c) for c in clients] == [200] * CAP
    finally:
        for c in clients:
            api.run(c.aclose())
