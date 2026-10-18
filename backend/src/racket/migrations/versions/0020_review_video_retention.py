"""FR-008 review video retention (ST-069; api-sprint-04 §5; ADR 0006; SEC-4 T4-RT-1).

* ``retention_settings``: one row per account that chose how long its review video is kept
  (``review_video_days``: whole days >= 1, or NULL for "until I delete"). No row means the
  configured default (``RETENTION_DEFAULT_DAYS``). Keyed by the account only, deleted with it.

The deletion date itself is not stored: it is computed from the probe's success time and the
current choice, so a changed choice applies to every match at the next purge pass.

Grants as 0012/0013: nothing for PUBLIC, nothing for the media worker role.

Revision ID: 0020
Revises: 0019
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retention_settings",
        sa.Column(
            "account_id",
            sa.Uuid(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE", name="retention_settings_account_fk"),
            primary_key=True,
        ),
        sa.Column("review_video_days", sa.Integer(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "review_video_days IS NULL OR review_video_days >= 1",
            name="retention_settings_days_positive",
        ),
    )
    op.execute("REVOKE ALL ON TABLE retention_settings FROM PUBLIC")


def downgrade() -> None:
    op.drop_table("retention_settings")
