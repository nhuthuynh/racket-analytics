"""Magic-link sign-in, pure domain parts (ST-013; ADR 0025; api-sprint-01 §2; threat model
T-ML-1/2/7/8/11). sprint-01 §5 order for ``MagicLinkToken``: 1. used token rejected; 2. token
older than 15 min rejected (injected clock, QD-TR-02); 3. token bound to one email.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.players.domain import (
    LinkExpired,
    MagicLinkToken,
    SessionLifetime,
    client_ip,
    email_key,
    normalise_email,
    sign_in_link_url,
)

T0 = datetime(2026, 10, 5, 9, 0, tzinfo=UTC)
TTL = timedelta(minutes=15)
KEY = b"unit-test-email-key"


def issue(at: datetime = T0, email: str = "ivy@example.com") -> tuple[MagicLinkToken, str]:
    return MagicLinkToken.issue(email_key=email_key(KEY, email), now=at, ttl=TTL)


# ---------------------------------------------------------------- 1. used token rejected
def test_a_used_link_is_refused() -> None:
    link, _ = issue()
    used = link.use(now=T0 + timedelta(minutes=1))
    with pytest.raises(LinkExpired):
        used.use(now=T0 + timedelta(minutes=2))


# ---------------------------------------------------------------- 2. older than the TTL
@pytest.mark.parametrize("age", [TTL, TTL + timedelta(seconds=1), timedelta(minutes=16)])
def test_a_link_at_or_past_its_lifetime_is_refused(age: timedelta) -> None:
    link, _ = issue()
    with pytest.raises(LinkExpired):
        link.use(now=T0 + age)


def test_a_link_just_inside_its_lifetime_works() -> None:
    link, _ = issue()
    assert link.use(now=T0 + TTL - timedelta(seconds=1)).used_at == T0 + TTL - timedelta(seconds=1)


# ---------------------------------------------------------------- 3. bound to one email
def test_a_link_signs_in_only_the_address_it_was_sent_to() -> None:
    ivy, _ = issue(email="ivy@example.com")
    carlos, _ = issue(email="carlos@example.com")
    assert ivy.email_key == email_key(KEY, "ivy@example.com")
    assert ivy.email_key != carlos.email_key


# ---------------------------------------------------------------- T-ML-1: token shape, hash at rest
def test_the_token_is_43_base64url_characters_and_only_its_hash_is_kept() -> None:
    link, token = issue()
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", token)
    assert link.token_sha256 == hashlib.sha256(token.encode()).hexdigest()
    assert token not in repr(link)
    assert issue()[1] != token  # CSPRNG, never repeated


def test_digest_of_matches_the_stored_hash() -> None:
    link, token = issue()
    assert MagicLinkToken.digest_of(token) == link.token_sha256


# ---------------------------------------------------------------- email address rules (§2.1)
@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Ivy@Example.COM", "ivy@example.com"), ("  ivy@example.com \t", "ivy@example.com"),
     ("a@b.c", "a@b.c")],
)  # fmt: skip
def test_well_formed_addresses_are_trimmed_and_lowercased(raw: str, expected: str) -> None:
    assert normalise_email(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "ivy", "ivy@", "@example.com", "ivy@example", "ivy@@example.com", "iv y@example.com",
     "a@b", "x" * 250 + "@ex.com", 42, None],
)  # fmt: skip
def test_malformed_addresses_are_refused(raw: object) -> None:
    assert normalise_email(raw) is None


@given(st.text(max_size=300))
def test_normalise_email_never_raises_and_output_is_well_formed(raw: str) -> None:
    """Parser of untrusted input (retro 0 L4)."""
    out = normalise_email(raw)
    if out is not None:
        assert 3 <= len(out) <= 254
        assert out.count("@") == 1
        assert "." in out.split("@")[1]
        assert not any(ch.isspace() for ch in out)


def test_email_key_is_16_hex_and_keyed() -> None:
    a = email_key(KEY, "ivy@example.com")
    assert re.fullmatch(r"[0-9a-f]{16}", a)
    assert email_key(b"other-key", "ivy@example.com") != a
    assert "ivy" not in a


# ---------------------------------------------------------------- T-ML-7: link base from config
def test_the_link_uses_the_configured_origin_and_a_fragment() -> None:
    url = sign_in_link_url("https://app.racket.test/", "A" * 43)
    assert url == "https://app.racket.test/auth/callback#token=" + "A" * 43


# ---------------------------------------------------------------- T-ML-11: session lifetimes
LIFE = SessionLifetime(absolute=timedelta(days=30), idle=timedelta(days=7))


def test_a_session_idle_for_seven_days_is_over() -> None:
    assert LIFE.is_valid(created_at=T0, last_seen_at=T0, now=T0 + timedelta(days=7)) is False
    assert LIFE.is_valid(created_at=T0, last_seen_at=T0, now=T0 + timedelta(days=6, hours=23))


def test_a_session_older_than_thirty_days_is_over_even_when_active() -> None:
    now = T0 + timedelta(days=30)
    assert LIFE.is_valid(created_at=T0, last_seen_at=now - timedelta(minutes=1), now=now) is False


def test_last_seen_is_refreshed_at_most_hourly() -> None:
    assert LIFE.needs_touch(last_seen_at=T0, now=T0 + timedelta(minutes=59)) is False
    assert LIFE.needs_touch(last_seen_at=T0, now=T0 + timedelta(hours=1)) is True


# ---------------------------------------------------------------- T-ML-8: client IP
@pytest.mark.parametrize(
    ("xff", "peer", "hops", "expected"),
    [
        ("203.0.113.9", "10.0.0.1", 0, "10.0.0.1"),  # no trusted proxy: the socket peer
        ("198.51.100.7, 203.0.113.9", "10.0.0.1", 1, "203.0.113.9"),  # right-most hop
        ("1.1.1.1, 198.51.100.7, 203.0.113.9", "10.0.0.1", 2, "198.51.100.7"),
        ("203.0.113.9", "10.0.0.1", 2, "10.0.0.1"),  # too few hops: never trust the left-most
        ("not-an-ip", "10.0.0.1", 1, "10.0.0.1"),
        ("", "10.0.0.1", 1, "10.0.0.1"),
        (None, None, 0, "unknown"),
    ],
)
def test_client_ip_counts_trusted_hops_from_the_right(
    xff: str | None, peer: str | None, hops: int, expected: str
) -> None:
    assert client_ip(xff, peer, hops) == expected


@given(st.text(max_size=200), st.integers(min_value=0, max_value=3))
def test_client_ip_never_raises(xff: str, hops: int) -> None:
    assert client_ip(xff, "10.0.0.1", hops)


# ---------------------------------------------------------------- the email (api-sprint-01 §2.1)
def test_the_email_has_the_link_the_promise_and_no_remote_content() -> None:
    from racket.players.domain import SignInEmail

    url = sign_in_link_url("https://app.racket.test", "A" * 43)
    mail = SignInEmail.compose(url, TTL)
    assert mail.subject == "Your sign-in link"
    for body in (mail.text, mail.html):
        assert url in body
        assert "It works once and expires in 15 minutes." in body
        assert "If you did not ask for it, ignore this email." in body
    assert "<img" not in mail.html
    assert "src=" not in mail.html
    assert "A" * 43 not in repr(mail)
