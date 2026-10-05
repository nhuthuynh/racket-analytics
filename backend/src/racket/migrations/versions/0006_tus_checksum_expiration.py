"""tus checksum and expiration extensions: expiry and creation metadata on upload sessions
(ST-017; api-sprint-01 §6.3, §6.4).

Revision ID: 0006
Revises: 0005
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "upload_sessions", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute("UPDATE upload_sessions SET expires_at = created_at + interval '24 hours'")
    op.alter_column("upload_sessions", "expires_at", nullable=False)
    # Display and resume-check only; never in object keys, logs or metrics (T-UV-9).
    op.add_column("upload_sessions", sa.Column("file_name", sa.String(255), nullable=True))
    op.add_column(
        "upload_sessions", sa.Column("file_last_modified_ms", sa.BigInteger(), nullable=True)
    )
    op.add_column("upload_sessions", sa.Column("head_sha256", sa.String(64), nullable=True))
    # Quota checks count an owner's open sessions (T-UV-7).
    op.create_index("ix_upload_sessions_owner_status", "upload_sessions", ["owner_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_upload_sessions_owner_status", "upload_sessions")
    for column in ("head_sha256", "file_last_modified_ms", "file_name", "expires_at"):
        op.drop_column("upload_sessions", column)
