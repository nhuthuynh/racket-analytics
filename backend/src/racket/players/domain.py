"""Identity & Players domain: magic-link sign-in values (ST-013; ADR 0025; api-sprint-01 §2).

Pure Python (ddd-guidelines §4.5): the clock is always an input, and the only randomness is
the token factory, which defaults to the CSPRNG and can be injected. Raw tokens and email
addresses never reach ``repr`` or logs; only SHA-256 digests and HMAC ``email_key`` values do
(T-ML-1, T-ML-9).
"""

from __future__ import annotations

import hashlib
import hmac
import html
import ipaddress
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

EMAIL_MIN, EMAIL_MAX = 3, 254
TOKEN_BYTES = 32  # 256 bits -> 43 base64url characters (ASVS 6.5.3, 6.5.4)
TOUCH_EVERY = timedelta(hours=1)


class LinkExpired(Exception):
    """Unknown, already used or too old: one outcome for all three (flows D-4)."""


def normalise_email(raw: object) -> str | None:
    """The address for lookup, or ``None`` when it is not well formed (api-sprint-01 §2.1):
    after trim, 3-254 characters, exactly one ``@``, no whitespace, a dot in the domain part.
    Lower-cased (judgment)."""
    if not isinstance(raw, str):
        return None
    email = raw.strip().lower()
    if not EMAIL_MIN <= len(email) <= EMAIL_MAX or email.count("@") != 1:
        return None
    if any(ch.isspace() for ch in email):
        return None
    local, domain = email.split("@")
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        return None
    return email


def email_key(secret: bytes, email: str) -> str:
    """Pseudonymous key of an address: first 16 hex of HMAC-SHA256 (ADR 0025 logging)."""
    return hmac.new(secret, email.encode(), hashlib.sha256).hexdigest()[:16]


def sign_in_link_url(public_web_origin: str, token: str) -> str:
    """The emailed link. The origin comes from configuration, never the request (T-ML-7);
    the token is in the fragment, so it never reaches a server log (T-ML-4)."""
    return f"{public_web_origin.rstrip('/')}/auth/callback#token={token}"


@dataclass(frozen=True)
class MagicLinkToken:
    """One emailed sign-in link, as stored: only the token's SHA-256 is kept."""

    token_sha256: str
    email_key: str
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None = None

    @staticmethod
    def digest_of(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def issue(
        cls,
        *,
        email_key: str,
        now: datetime,
        ttl: timedelta,
        token_factory: Callable[[], str] = lambda: secrets.token_urlsafe(TOKEN_BYTES),
    ) -> tuple[MagicLinkToken, str]:
        """A new link and its raw token (the token goes into the email, never into storage)."""
        token = token_factory()
        link = cls(cls.digest_of(token), email_key, now, now + ttl)
        return link, token

    def use(self, *, now: datetime) -> MagicLinkToken:
        """Single use within the lifetime (ASVS 6.5.1, 6.5.5). The database enforces the same
        rule atomically with a conditional update (T-ML-3)."""
        if self.used_at is not None or now >= self.expires_at:
            raise LinkExpired("link can no longer be used")
        return replace(self, used_at=now)


@dataclass(frozen=True)
class SessionLifetime:
    """ADR 0025: absolute and inactivity limits (ASVS 7.3.1, 7.3.2)."""

    absolute: timedelta
    idle: timedelta

    def is_valid(self, *, created_at: datetime, last_seen_at: datetime, now: datetime) -> bool:
        return now < created_at + self.absolute and now < last_seen_at + self.idle

    def needs_touch(self, *, last_seen_at: datetime, now: datetime) -> bool:
        """``last_seen_at`` is written at most once per hour per session (ADR 0025)."""
        return now - last_seen_at >= TOUCH_EVERY


def client_ip(forwarded_for: str | None, peer: str | None, trusted_hops: int) -> str:
    """The address ``trusted_hops`` from the right of ``X-Forwarded-For``, else the socket
    peer; never the left-most value a client can forge (api-sprint-01 §2.4, T-ML-8)."""
    fallback = peer or "unknown"
    if trusted_hops <= 0 or not forwarded_for:
        return fallback
    hops = [part.strip() for part in forwarded_for.split(",")]
    if len(hops) < trusted_hops:
        return fallback
    candidate = hops[-trusted_hops]
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return fallback


@dataclass(frozen=True)
class SignInEmail:
    """The sign-in email (api-sprint-01 §2.1): plain text and HTML, no remote images or
    tracking. ``repr`` hides the body, which holds the token."""

    subject: str
    text: str = field(repr=False)
    html: str = field(repr=False)

    @classmethod
    def compose(cls, link_url: str, ttl: timedelta) -> SignInEmail:
        minutes = max(1, round(ttl.total_seconds() / 60))
        notice = (
            f"It works once and expires in {minutes} minutes. "
            "If you did not ask for it, ignore this email."
        )
        text = f"Sign in to racket-analytics:\n\n{link_url}\n\n{notice}\n"
        safe = html.escape(link_url, quote=True)
        body = (
            "<!doctype html><html><body>"
            f'<p><a href="{safe}">Sign in to racket-analytics</a></p>'
            f"<p>{safe}</p><p>{html.escape(notice)}</p></body></html>"
        )
        return cls(subject="Your sign-in link", text=text, html=body)
