"""The last refusal of a file for a match (ST-018; api-sprint-01 §5.2 ``rejection``).

Revision ID: 0007
Revises: 0006
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("rejection_code", sa.String(32), nullable=True))
    op.add_column("matches", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "rejected_at")
    op.drop_column("matches", "rejection_code")
