"""FR-003 age confirmation (ST-068a; api-sprint-04 §4; SEC-4 T4-AG-1, T4-AG-3).

* ``accounts.age_confirmed_at``: when the holder confirmed being an adult. Only the timestamp is
  stored; there is no birth date or age column.
* ``pending_sign_ins``: a signed-in address without an account while ``FEATURE_AGE_GATE`` is on,
  keyed by the session token's SHA-256. Deleted on either answer and when it expires (at most
  24 h); a refused answer leaves no row.

Grants as 0012/0013: nothing for PUBLIC, nothing for the media worker role.

Revision ID: 0019
Revises: 0018
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    at = sa.DateTime(timezone=True)
    op.add_column("accounts", sa.Column("age_confirmed_at", at, nullable=True))
    op.create_table(
        "pending_sign_ins",
        sa.Column("token_sha256", sa.String(64), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("email_key", sa.String(64), nullable=False),
        sa.Column("created_at", at, nullable=False),
        sa.Column("expires_at", at, nullable=False),
    )
    op.execute("REVOKE ALL ON TABLE pending_sign_ins FROM PUBLIC")


def downgrade() -> None:
    op.drop_table("pending_sign_ins")
    op.drop_column("accounts", "age_confirmed_at")
