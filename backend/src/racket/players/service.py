"""Identity application services: sessions, the dev provider and magic-link sign-in
(ST-006, ST-013; api-sprint-00 §2, api-sprint-01 §2; ADR 0025).

Session tokens and link tokens are 32 CSPRNG bytes, base64url; only their SHA-256 is stored and
they are never logged (ASVS 7.2.3, 11.5.1; AQS/SEC-04 16.2.5). The seeded dev users exist only
when the dev provider is enabled and APP_ENV is dev or test (ASVS 6.3.2). Security events go to
``racket.security`` with UTC ``time``, the request ID (from the log context) and ``account_id``
or ``email_key``; never an address, token or token hash (NFR-057, T-ML-9).
"""

from __future__ import annotations

import logging
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from racket.analysis_jobs.domain import JobKey
from racket.analysis_jobs.queue import JobQueue
from racket.platform.errors import AppError, FieldError, ValidationFailed
from racket.platform.logs import SECURITY_LOGGER, user_id_var
from racket.platform.ratelimit import RateLimited, RateLimiter
from racket.platform.settings import Settings
from racket.players.domain import (
    LinkExpired,
    MagicLinkToken,
    SessionLifetime,
    email_key,
    normalise_email,
)
from racket.players.models import accounts, sessions, sign_in_links, sign_in_requests

# "dana" never gets a match from any spec: the E2E empty-state check signs in as her (QA-R1-04).
DEV_USERS = {"ivy": "Ivy", "carlos": "Carlos", "dana": "Dana"}
DEV_SESSION_LIFETIME = timedelta(hours=12)
SEND_SIGN_IN_LINK = "send_sign_in_link"

security_log = logging.getLogger(SECURITY_LOGGER)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def security_event(message: str, event: str, **fields: Any) -> None:
    """One attributable auth log line (NFR-057). ``fields`` must hold no personal data."""
    when = _utcnow().isoformat(timespec="milliseconds").replace("+00:00", "Z")
    security_log.info(message, extra={"event": event, "time": when, **fields})


@dataclass(frozen=True)
class Account:
    id: uuid.UUID
    display_name: str | None


def token_digest(token: str) -> str:
    return MagicLinkToken.digest_of(token)


class LinkRefused(AppError):
    """401 ``link_expired`` for unknown, used and expired links alike (flows D-4)."""

    status, code = 401, "link_expired"


class IdentityService:
    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.session = session
        self.settings = settings
        self.clock = clock

    # ------------------------------------------------------------ sessions (ADR 0025)
    @property
    def lifetime(self) -> SessionLifetime:
        s = self.settings
        if s is None:
            return SessionLifetime(absolute=timedelta(days=30), idle=timedelta(days=7))
        return SessionLifetime(
            absolute=timedelta(seconds=s.session_absolute_seconds),
            idle=timedelta(seconds=s.session_idle_seconds),
        )

    def start_session(
        self,
        account_id: uuid.UUID,
        previous_token: str | None,
        absolute: timedelta | None = None,
        *,
        prune: bool = True,
    ) -> str:
        """A new session (rotated: any presented session is deleted first, ASVS 7.2.4). At most
        ``SESSION_MAX_PER_ACCOUNT`` sessions per account: the oldest go (ASVS 7.1.2). The dev
        provider's shared seeded users are exempt (parallel E2E workers, judgment)."""
        if previous_token:
            self._delete_session(previous_token)
        token = secrets.token_urlsafe(32)
        now = self.clock()
        self.session.execute(
            sa.insert(sessions).values(
                token_sha256=token_digest(token),
                account_id=account_id,
                created_at=now,
                expires_at=now + (absolute or self.lifetime.absolute),
                last_seen_at=now,
            )
        )
        if not prune:
            return token
        keep = self.settings.session_max_per_account if self.settings else 10
        newest = (
            sa.select(sessions.c.token_sha256)
            .where(sessions.c.account_id == account_id)
            .order_by(sessions.c.created_at.desc(), sessions.c.token_sha256)
            .limit(keep)
        )
        self.session.execute(
            sa.delete(sessions).where(
                sessions.c.account_id == account_id, sessions.c.token_sha256.not_in(newest)
            )
        )
        return token

    def _delete_session(self, token: str) -> uuid.UUID | None:
        deleted: uuid.UUID | None = self.session.execute(
            sa.delete(sessions)
            .where(sessions.c.token_sha256 == token_digest(token))
            .returning(sessions.c.account_id)
        ).scalar_one_or_none()
        return deleted

    def sign_out(self, token: str) -> None:
        account_id = self._delete_session(token)
        self.session.commit()
        if account_id is not None:
            security_event("auth.signed_out", "auth.signed_out", account_id=str(account_id))

    def account_for_token(self, token: str) -> Account | None:
        now = self.clock()
        row = self.session.execute(
            sa.select(
                accounts.c.id, accounts.c.display_name, sessions.c.created_at,
                sessions.c.last_seen_at,
            )
            .join(sessions, sessions.c.account_id == accounts.c.id)
            .where(sessions.c.token_sha256 == token_digest(token), sessions.c.expires_at > now)
        ).one_or_none()  # fmt: skip
        if row is None:
            return None
        life = self.lifetime
        if not life.is_valid(created_at=row.created_at, last_seen_at=row.last_seen_at, now=now):
            return None
        if life.needs_touch(last_seen_at=row.last_seen_at, now=now):
            self.session.execute(
                sa.update(sessions)
                .where(sessions.c.token_sha256 == token_digest(token))
                .values(last_seen_at=now)
            )
            self.session.commit()
        return Account(row.id, row.display_name)

    # ------------------------------------------------------------ dev provider (ST-006)
    def seed_dev_users(self) -> None:
        now = self.clock()
        for username, display_name in DEV_USERS.items():
            self.session.execute(
                insert(accounts)
                .values(
                    id=uuid.uuid4(), username=username, display_name=display_name, created_at=now
                )
                .on_conflict_do_nothing(index_elements=["username"])
            )
        self.session.commit()

    def dev_users(self) -> list[dict[str, str]]:
        return [{"username": u, "display_name": d} for u, d in DEV_USERS.items()]

    def sign_in(self, username: str, previous_token: str | None) -> tuple[Account, str] | None:
        """A new session for a seeded user, or None. Any presented session is deleted first."""
        if previous_token:
            self._delete_session(previous_token)
        row = None
        if username in DEV_USERS:
            row = self.session.execute(
                sa.select(accounts.c.id, accounts.c.display_name).where(
                    accounts.c.username == username
                )
            ).one_or_none()
        if row is None:
            self.session.commit()
            return None
        token = self.start_session(row.id, None, absolute=DEV_SESSION_LIFETIME, prune=False)
        self.session.commit()
        return Account(row.id, row.display_name), token


@dataclass(frozen=True)
class Exchanged:
    account: Account
    session_token: str
    new_account: bool


class MagicLinkService:
    """``POST /auth/links`` and ``POST /auth/exchange`` (api-sprint-01 §2.1, §2.2)."""

    def __init__(
        self, session: Session, settings: Settings, clock: Callable[[], datetime] = _utcnow
    ) -> None:
        self.session = session
        self.settings = settings
        self.clock = clock
        self.limiter = RateLimiter(session, clock=clock)
        self.window = timedelta(seconds=settings.auth_window_seconds)

    def _limit(self, key: str, limit: int, **log_fields: Any) -> None:
        """Count a hit and commit it, whatever happens next; refuse over the limit."""
        retry_at = self.limiter.hit(key, limit=limit, window=self.window)
        self.session.commit()
        if retry_at is not None:
            kind = key.rsplit(":", 1)[0]  # e.g. "link:email"; never the key's value
            security_event("auth.rate_limited", "auth.rate_limited", limit=kind, **log_fields)
            raise RateLimited(retry_at, self.clock())

    def request_link(self, raw_email: object, ip: str) -> None:
        """Queue a sign-in email. Same response for every well-formed address: the account
        lookup happens only at the exchange (no existence oracle, T-ML-6)."""
        email = normalise_email(raw_email)
        if email is None:
            raise ValidationFailed("email", [FieldError("email", "email_invalid")])
        key = email_key(self.settings.auth_email_key.encode(), email)
        self._limit(f"link:ip:{ip}", self.settings.auth_link_limit_per_ip, email_key=key)
        self._limit(f"link:email:{key}", self.settings.auth_link_limit_per_email, email_key=key)
        request_id = uuid.uuid4()
        self.session.execute(
            sa.insert(sign_in_requests).values(
                id=request_id, email=email, email_key=key, created_at=self.clock()
            )
        )
        JobQueue(self.session).enqueue(
            JobKey(request_id, self.settings.pipeline_version, SEND_SIGN_IN_LINK)
        )
        self.session.commit()
        security_event("auth.link_requested", "auth.link_requested", email_key=key)

    def exchange(self, token: str, ip: str, previous_token: str | None) -> Exchanged:
        self._limit(f"exchange:ip:{ip}", self.settings.auth_exchange_limit_per_ip)
        now = self.clock()
        digest = MagicLinkToken.digest_of(token)
        row = self.session.execute(
            sa.select(sign_in_links).where(sign_in_links.c.token_sha256 == digest).with_for_update()
        ).one_or_none()
        try:
            if row is None:
                raise LinkExpired("unknown link")
            used = MagicLinkToken.from_row(row._mapping).use(now=now)  # T-ML-2; lock: T-ML-3
        except LinkExpired:
            if row is not None and row.email is not None:
                # ADR 0032: a refused link keeps no address (until the ST-038 sweep exists).
                self.session.execute(
                    sa.update(sign_in_links)
                    .where(sign_in_links.c.token_sha256 == digest)
                    .values(email=None)
                )
                self.session.commit()
            else:
                self.session.rollback()
            security_event(
                "auth.link_refused", "auth.refused", email_key=row.email_key if row else None
            )
            raise LinkRefused("link refused") from None
        self.session.execute(
            sa.update(sign_in_links)
            .where(sign_in_links.c.token_sha256 == digest)
            .values(used_at=used.used_at, email=None)  # ADR 0032: the address leaves the link
        )
        if row.email is None:  # a link issued before migration 0008 (ADR 0032 legacy path)
            account, new_account = self._legacy_account_for(used.email_key, now)
        else:
            account, new_account = self._account_for(row.email, used.email_key, now)
        identity = IdentityService(self.session, self.settings, self.clock)
        session_token = identity.start_session(account.id, previous_token)
        self.session.commit()
        user_id_var.set(str(account.id))
        security_event(
            "auth.link_exchanged", "auth.exchanged", account_id=str(account.id),
            new_account=new_account,
        )  # fmt: skip
        return Exchanged(account, session_token, new_account)

    def _account_for(self, email: str, key: str, now: datetime) -> tuple[Account, bool]:
        """The account for this address, created at its first successful exchange (ADR 0032:
        the stored normalised address is the identity; ``email_key`` is only a pseudonym)."""
        found = self._account_by_email(email)
        if found is not None:
            return found, False
        claimed = self.session.execute(
            sa.update(accounts)
            .where(
                accounts.c.id
                == sa.select(accounts.c.id)
                .where(accounts.c.email_key == key, accounts.c.email.is_(None))
                .order_by(accounts.c.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
                .scalar_subquery()
            )
            .values(email=email)
            .returning(accounts.c.id, accounts.c.display_name)
        ).one_or_none()
        if claimed is not None:  # a legacy account (email IS NULL) is claimed once
            return Account(claimed.id, claimed.display_name), False
        created = self.session.execute(
            insert(accounts)
            .values(id=uuid.uuid4(), email=email, email_key=key, created_at=now)
            .on_conflict_do_nothing(index_elements=["email"])
            .returning(accounts.c.id, accounts.c.display_name)
        ).one_or_none()
        if created is not None:
            return Account(created.id, created.display_name), True
        raced = self.session.execute(  # a parallel first exchange for the address won
            sa.select(accounts.c.id, accounts.c.display_name).where(accounts.c.email == email)
        ).one()
        return Account(raced.id, raced.display_name), False

    def _account_by_email(self, email: str) -> Account | None:
        row = self.session.execute(
            sa.select(accounts.c.id, accounts.c.display_name).where(accounts.c.email == email)
        ).one_or_none()
        return None if row is None else Account(row.id, row.display_name)

    def _legacy_account_for(self, key: str, now: datetime) -> tuple[Account, bool]:
        """Sprint 1 behaviour for a link without an address: the account by ``email_key``
        among accounts not yet claimed by an address. Dev data only; removed one release after
        migration 0008 (ADR 0032), once no such link or seed (IT-01 session controls) remains."""
        row = self.session.execute(
            sa.select(accounts.c.id, accounts.c.display_name)
            .where(accounts.c.email_key == key, accounts.c.email.is_(None))
            .order_by(accounts.c.created_at)
            .limit(1)
            .with_for_update()
        ).one_or_none()
        if row is not None:
            return Account(row.id, row.display_name), False
        created = self.session.execute(
            insert(accounts)
            .values(id=uuid.uuid4(), email_key=key, created_at=now)
            .returning(accounts.c.id, accounts.c.display_name)
        ).one()
        return Account(created.id, created.display_name), True
