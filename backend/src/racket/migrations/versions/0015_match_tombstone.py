"""``matches.deleted_at``: a deleted match is hidden at once and purged later (ST-050;
deletion-and-purge.md §3.1; ADR 0042). The partial index serves the purge's "due" scan.

Revision ID: 0015
Revises: 0014
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_matches_deleted_at",
        "matches",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_matches_deleted_at", table_name="matches")
    op.drop_column("matches", "deleted_at")
