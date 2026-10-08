"""``accounts.deleted_at``: a deleted account is a tombstone with no personal data until the
purge removes it (ST-051; deletion-and-purge.md §3.2; FR-007).

Revision ID: 0016
Revises: 0015
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "deleted_at")
