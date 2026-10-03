"""The dev/test identity provider and session tokens (ST-006; api-sprint-00 §2).

Tokens are 32 CSPRNG bytes, base64url; only their SHA-256 is stored and they are never logged
(ASVS 7.2.3, 11.5.1; AQS/SEC-04 16.2.5). The seeded users exist only when the dev provider is
enabled and APP_ENV is dev or test (ASVS 6.3.2).
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from racket.players.models import accounts, sessions

# "dana" never gets a match from any spec: the E2E empty-state check signs in as her (QA-R1-04).
DEV_USERS = {"ivy": "Ivy", "carlos": "Carlos", "dana": "Dana"}
DEV_SESSION_LIFETIME = timedelta(hours=12)


@dataclass(frozen=True)
class Account:
    id: uuid.UUID
    display_name: str


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class IdentityService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def seed_dev_users(self) -> None:
        now = datetime.now(UTC)
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
            self.sign_out(previous_token)
        if username not in DEV_USERS:
            self.session.commit()
            return None
        row = self.session.execute(
            sa.select(accounts.c.id, accounts.c.display_name).where(accounts.c.username == username)
        ).one_or_none()
        if row is None:
            self.session.commit()
            return None
        token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        self.session.execute(
            sa.insert(sessions).values(
                token_sha256=token_digest(token),
                account_id=row.id,
                created_at=now,
                expires_at=now + DEV_SESSION_LIFETIME,
            )
        )
        self.session.commit()
        return Account(row.id, row.display_name), token

    def sign_out(self, token: str) -> None:
        self.session.execute(
            sa.delete(sessions).where(sessions.c.token_sha256 == token_digest(token))
        )
        self.session.commit()

    def account_for_token(self, token: str) -> Account | None:
        row = self.session.execute(
            sa.select(accounts.c.id, accounts.c.display_name)
            .join(sessions, sessions.c.account_id == accounts.c.id)
            .where(
                sessions.c.token_sha256 == token_digest(token),
                sessions.c.expires_at > datetime.now(UTC),
            )
        ).one_or_none()
        return None if row is None else Account(row.id, row.display_name)
