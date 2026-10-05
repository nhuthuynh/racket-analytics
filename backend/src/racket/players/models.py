"""Identity & Players tables (ST-006, ST-013). Only this context reads them (context map rule 1)."""

from __future__ import annotations

import sqlalchemy as sa

from racket.platform.db import metadata

accounts = sa.Table(
    "accounts",
    metadata,
    sa.Column("id", sa.Uuid(), primary_key=True),
    sa.Column("username", sa.String(64), nullable=True, unique=True),  # dev provider only
    sa.Column("display_name", sa.String(120), nullable=True),
    # ADR 0032: the normalised address is the identity (unique); never logged or returned.
    sa.Column("email", sa.String(254), nullable=True, unique=True),
    # Log and rate-limit pseudonym only (ADR 0025); not unique since ADR 0032.
    sa.Column("email_key", sa.String(64), nullable=True, index=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

sessions = sa.Table(
    "sessions",
    metadata,
    sa.Column("token_sha256", sa.String(64), primary_key=True),
    sa.Column("account_id", sa.Uuid(), sa.ForeignKey("accounts.id", ondelete="CASCADE")),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),  # absolute limit
    sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),  # idle limit
)

sign_in_links = sa.Table(
    "sign_in_links",
    metadata,
    sa.Column("token_sha256", sa.String(64), primary_key=True),
    sa.Column("email_key", sa.String(64), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    # ADR 0032: the address rides the link to the exchange; NULL once used or refused.
    sa.Column("email", sa.String(254), nullable=True),
)

sign_in_requests = sa.Table(
    "sign_in_requests",
    metadata,
    sa.Column("id", sa.Uuid(), primary_key=True),
    sa.Column("email", sa.String(254), nullable=False),
    sa.Column("email_key", sa.String(64), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)
