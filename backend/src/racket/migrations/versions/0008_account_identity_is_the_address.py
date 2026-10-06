"""Account identity is the stored normalised address, not the HMAC ``email_key``
(ST-013b; ADR 0032 option 1; SEC-R3-S1-01 / SEC-R4-S1-01).

``accounts.email`` is unique and is the identity; ``accounts.email_key`` stays as the log and
rate-limit pseudonym only and is no longer unique. ``sign_in_links.email`` carries the address
from the outbox to the exchange and is nulled when the link is used or refused.

Revision ID: 0008
Revises: 0007
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("email", sa.String(254), nullable=True))
    op.create_unique_constraint("uq_accounts_email", "accounts", ["email"])
    op.drop_constraint("uq_accounts_email_key", "accounts", type_="unique")
    op.create_index("ix_accounts_email_key", "accounts", ["email_key"])  # legacy claim lookup
    op.add_column("sign_in_links", sa.Column("email", sa.String(254), nullable=True))


def downgrade() -> None:
    op.drop_column("sign_in_links", "email")
    op.drop_index("ix_accounts_email_key", "accounts")
    op.create_unique_constraint("uq_accounts_email_key", "accounts", ["email_key"])
    op.drop_constraint("uq_accounts_email", "accounts", type_="unique")
    op.drop_column("accounts", "email")
