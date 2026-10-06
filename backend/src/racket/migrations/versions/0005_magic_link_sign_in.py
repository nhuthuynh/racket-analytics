"""Magic-link sign-in: links, the outbox of link requests, session lifetimes, rate limits
(ST-013; ADR 0025; api-sprint-01 §2).

Revision ID: 0005
Revises: 0004
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Magic-link accounts have no username and no display name yet (api-sprint-01 §2.3).
    op.alter_column("accounts", "username", existing_type=sa.String(64), nullable=True)
    op.alter_column("accounts", "display_name", existing_type=sa.String(120), nullable=True)
    # The address is never stored on the account: only its HMAC key (T-ML-9, T-ML-14).
    op.add_column("accounts", sa.Column("email_key", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_accounts_email_key", "accounts", ["email_key"])

    op.add_column("sessions", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE sessions SET last_seen_at = created_at")
    op.alter_column("sessions", "last_seen_at", nullable=False)

    op.create_table(
        "sign_in_links",
        sa.Column("token_sha256", sa.String(64), primary_key=True),  # never the token (T-ML-1)
        sa.Column("email_key", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        # Outbox: the address waits here for the send_sign_in_link job, which deletes the row
        # in the transaction that records the sent link (data minimisation, judgment).
        "sign_in_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("email_key", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "rate_limit_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rate_limit_events_key_at", "rate_limit_events", ["key", "at"])


def downgrade() -> None:
    op.drop_table("rate_limit_events")
    op.drop_table("sign_in_requests")
    op.drop_table("sign_in_links")
    op.drop_column("sessions", "last_seen_at")
    op.drop_constraint("uq_accounts_email_key", "accounts")
    op.drop_column("accounts", "email_key")
    op.alter_column("accounts", "display_name", existing_type=sa.String(120), nullable=False)
    op.alter_column("accounts", "username", existing_type=sa.String(64), nullable=False)
