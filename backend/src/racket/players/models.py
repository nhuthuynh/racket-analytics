"""Identity & Players tables (ST-006). Only this context reads them (context map rule 1)."""

from __future__ import annotations

import sqlalchemy as sa

from racket.platform.db import metadata

accounts = sa.Table(
    "accounts",
    metadata,
    sa.Column("id", sa.Uuid(), primary_key=True),
    sa.Column("username", sa.String(64), nullable=False, unique=True),
    sa.Column("display_name", sa.String(120), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

sessions = sa.Table(
    "sessions",
    metadata,
    sa.Column("token_sha256", sa.String(64), primary_key=True),
    sa.Column("account_id", sa.Uuid(), sa.ForeignKey("accounts.id", ondelete="CASCADE")),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
)
