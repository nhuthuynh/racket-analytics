"""Match setup answers and participants (ST-016; ADR 0024; api-sprint-01 §5).

Revision ID: 0004
Revises: 0003
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "matches",
        sa.Column("scoring_system", sa.String(32), nullable=False, server_default="side_out"),
    )
    op.add_column(
        "matches",
        sa.Column(
            "rules_version",
            sa.String(64),
            nullable=False,
            server_default="PROVISIONAL-UNVERIFIED",
        ),
    )
    op.add_column("matches", sa.Column("played_on", sa.Date(), nullable=True))
    op.create_table(
        "match_participants",
        sa.Column(
            "match_id",
            sa.Uuid(),
            sa.ForeignKey("matches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slot", sa.String(2), nullable=False),
        sa.Column("nickname", sa.String(30), nullable=False),
        sa.Column("is_me", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("match_id", "slot", name="pk_match_participants"),
        sa.CheckConstraint("slot IN ('A1', 'A2', 'B1', 'B2')", name="slot_known"),
    )
    # At most one "me" per match, whatever the code does (ADR 0024 invariant, defence in depth).
    op.create_index(
        "uq_match_participants_me",
        "match_participants",
        ["match_id"],
        unique=True,
        postgresql_where=sa.text("is_me"),
    )


def downgrade() -> None:
    op.drop_table("match_participants")
    op.drop_column("matches", "played_on")
    op.drop_column("matches", "rules_version")
    op.drop_column("matches", "scoring_system")
