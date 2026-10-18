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
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from racket.platform.errors import FieldError, ValidationFailed
from racket.platform.text import is_plain_line

EMAIL_MIN, EMAIL_MAX = 3, 254
TOKEN_BYTES = 32  # 256 bits -> 43 base64url characters (ASVS 6.5.3, 6.5.4)
TOUCH_EVERY = timedelta(hours=1)


class LinkExpired(Exception):
    """Unknown, already used or too old: one outcome for all three (flows D-4)."""


def normalise_email(raw: object) -> str | None:
    """The address for lookup, or ``None`` when it is not well formed (api-sprint-01 §2.1):
    after trim, 3-254 characters, exactly one ``@``, no whitespace, a dot in the domain part.
    Lower-cased (judgment). After the trim, a control, surrogate or line-separator character
    is refused (C-01, SEC-R6-S1-01): Postgres cannot store NUL, UTF-8 cannot encode a surrogate."""
    if not isinstance(raw, str):
        return None
    email = raw.strip().lower()
    if not is_plain_line(email):
        return None
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

    @classmethod
    def from_row(cls, row: Mapping[Any, Any]) -> MagicLinkToken:
        """The value from a ``sign_in_links`` row; the address column is not part of it."""
        return cls(
            row["token_sha256"], row["email_key"], row["created_at"], row["expires_at"],
            row["used_at"],
        )  # fmt: skip

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


# ---------------------------------------------------------------- FR-003 age confirmation
PENDING_SIGN_IN_TTL_MAX = timedelta(hours=24)  # SEC-4 T4-AG-3
AGE_ANSWER_FIELDS = frozenset({"is_adult", "confirm"})


class AgeOutcome(Enum):
    CONFIRM = "confirm"  # store age_confirmed_at (a pending sign-in becomes an account)
    END_PENDING = "end_pending"  # delete the pending sign-in; no account row is written
    DELETE_ACCOUNT = "delete_account"  # an existing account goes as ``DELETE /me`` does


@dataclass(frozen=True)
class AgeAnswer:
    """The answer to "Are you {age_minimum} or over?" (api-sprint-04 §4). Self-declared: no
    birth date or age is asked for or kept (OQ-05, T4-AG-1)."""

    is_adult: bool
    confirm_delete: bool = False

    @classmethod
    def parse(cls, body: object) -> AgeAnswer:
        """The closed body ``{"is_adult": bool, "confirm": "delete"}``; one field code on
        failure, never an echo of the input."""
        if body is None:
            body = {}
        if not isinstance(body, Mapping):
            raise ValidationFailed("age answer", [FieldError(None, "invalid")])
        if any(key not in AGE_ANSWER_FIELDS for key in body):
            raise ValidationFailed("age answer", [FieldError(None, "unknown_field")])
        if "is_adult" not in body:
            raise ValidationFailed("age answer", [FieldError("is_adult", "required")])
        if not isinstance(body["is_adult"], bool):
            raise ValidationFailed("age answer", [FieldError("is_adult", "invalid")])
        if body.get("confirm", "delete") != "delete":
            raise ValidationFailed("age answer", [FieldError("confirm", "invalid")])
        return cls(body["is_adult"], body.get("confirm") == "delete")

    def outcome(self, *, has_account: bool) -> AgeOutcome:
        """A pending sign-in holds no data, so ``false`` simply ends it. An existing account may
        hold matches, so ``false`` deletes it only with the typed confirmation of ``DELETE /me``
        (T4-AG-5)."""
        if self.is_adult:
            return AgeOutcome.CONFIRM
        if not has_account:
            return AgeOutcome.END_PENDING
        if not self.confirm_delete:
            raise ValidationFailed(
                "deletion not confirmed", [FieldError("confirm", "confirmation_required")]
            )
        return AgeOutcome.DELETE_ACCOUNT


@dataclass(frozen=True)
class AgeGate:
    """``FEATURE_AGE_GATE``: while on, only a holder with a confirmation time is admitted."""

    enabled: bool

    def admits(self, age_confirmed_at: datetime | None) -> bool:
        return not self.enabled or age_confirmed_at is not None


def pending_sign_in_expiry(now: datetime, session_absolute: timedelta) -> datetime:
    """A pending sign-in ends with its session, and after 24 h at the latest (T4-AG-3)."""
    return now + min(session_absolute, PENDING_SIGN_IN_TTL_MAX)


def under_age_message(age_minimum: int) -> str:
    """The ``under_age`` text: interim wording W-A07 (PM-4 register, pending legal review)."""
    return (
        f"You need to be {age_minimum} or over to use this app. We did not make an account for you."
    )


RETENTION_FIELD = "review_video_days"


@dataclass(frozen=True)
class RetentionChoice:
    """How long the player keeps their review video (FR-008; OQ-07; api-sprint-04 §5): one of
    the configured choices in whole days, or ``None`` for "until I delete". It belongs to the
    session account only: the closed body names no account (T4-RT-1)."""

    days: int | None

    @classmethod
    def parse(cls, body: object, choices: tuple[int | None, ...]) -> RetentionChoice:
        """The closed body ``{"review_video_days": <choice>}``; one field code on failure,
        never an echo of the input. A value must be exactly a choice: no string, float or
        boolean that happens to compare equal."""
        if not isinstance(body, Mapping):
            raise ValidationFailed("retention choice", [FieldError(None, "invalid")])
        if any(key != RETENTION_FIELD for key in body):
            raise ValidationFailed("retention choice", [FieldError(None, "unknown_field")])
        if RETENTION_FIELD not in body:
            raise ValidationFailed("retention choice", [FieldError(RETENTION_FIELD, "required")])
        value = body[RETENTION_FIELD]
        if not (value is None or type(value) is int) or value not in choices:
            raise ValidationFailed(
                "retention choice", [FieldError(RETENTION_FIELD, "unknown_value")]
            )
        return cls(value)


TRAINING_CONSENT_FIELD = "opt_in"


@dataclass(frozen=True)
class TrainingConsentChoice:
    """Whether the player lets their matches be used to train or evaluate models (FR-009; OQ-06;
    api-sprint-04 §6): a separate opt-in, off by default and revocable. It belongs to the
    session account only: the closed body names no account (T4-CS-4)."""

    opt_in: bool

    @classmethod
    def parse(cls, body: object) -> TrainingConsentChoice:
        """The closed body ``{"opt_in": true|false}``; one field code on failure, never an echo
        of the input. Only a JSON boolean: no string, number or null that reads as one."""
        if not isinstance(body, Mapping):
            raise ValidationFailed("training consent", [FieldError(None, "invalid")])
        if any(key != TRAINING_CONSENT_FIELD for key in body):
            raise ValidationFailed("training consent", [FieldError(None, "unknown_field")])
        if TRAINING_CONSENT_FIELD not in body:
            raise ValidationFailed(
                "training consent", [FieldError(TRAINING_CONSENT_FIELD, "required")]
            )
        value = body[TRAINING_CONSENT_FIELD]
        if type(value) is not bool:
            raise ValidationFailed(
                "training consent", [FieldError(TRAINING_CONSENT_FIELD, "invalid")]
            )
        return cls(value)
