"""Helpers for the FR-003 age gate tests (ST-068a; api-sprint-04 §4).

A sign-in link is seeded straight into ``sign_in_links`` (the stored shape of api-sprint-01
§2.2), so the tests exercise ``POST /auth/exchange`` without a mail server. Rows are counted with
plain SQL: the tests never import the product's tables.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import sqlalchemy as sa

AGE_CONFIRMATION = "/me/age-confirmation"


def seed_link(session: Any, email: str) -> str:
    """An unused, unexpired link for ``email``; returns its raw token."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    session.execute(
        sa.text(
            "INSERT INTO sign_in_links (token_sha256, email_key, created_at, expires_at, email) "
            "VALUES (:digest, :key, :now, :expires, :email)"
        ),
        {
            "digest": hashlib.sha256(token.encode()).hexdigest(),
            "key": secrets.token_hex(8),
            "now": now,
            "expires": now + timedelta(minutes=15),
            "email": email,
        },
    )
    session.commit()
    return token


def accounts_for(session: Any, email: str | None = None) -> list[Any]:
    """Account rows (all, or the live one of ``email``) with their confirmation time."""
    query = "SELECT id, age_confirmed_at, deleted_at FROM accounts"
    if email is not None:
        return list(session.execute(sa.text(query + " WHERE email = :e"), {"e": email}))
    return list(session.execute(sa.text(query)))


def pending_count(session: Any) -> int:
    return int(session.execute(sa.text("SELECT count(*) FROM pending_sign_ins")).scalar_one())


def age_like_columns(session: Any) -> set[str]:
    """Every column of the schema named like a birth date or an age (T4-AG-1 schema test)."""
    rows = session.execute(
        sa.text(
            "SELECT table_name || '.' || column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() "
            "AND (column_name ILIKE '%birth%' OR column_name ~* '(^|_)(age|dob)(_|$)')"
        )
    ).scalars()
    return {str(name) for name in rows}
