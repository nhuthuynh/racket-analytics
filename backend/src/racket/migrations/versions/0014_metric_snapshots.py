"""``metric_snapshots``: the starter stats of a match per dictionary and rules version (ST-046;
analytics-snapshots.md §6; ADR 0040).

Owned by Analytics. No foreign key to ``matches`` (context-map rule 1): the purge removes the
rows through ``analytics.public.purge_match``, and a write happens only under the match row
``FOR SHARE`` lock (invariant S8, ADR 0045). The media worker role gets nothing on it (ST-042).

Revision ID: 0014
Revises: 0013
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "metric_snapshots",
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("metric_def_version", sa.String(16), nullable=False),
        sa.Column("rules_version", sa.String(64), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("sheet_version", sa.Integer(), nullable=False),
        sa.Column("stats", JSONB(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sheet_version >= 0", name="sheet_version_not_negative"),
        sa.PrimaryKeyConstraint(
            "match_id", "metric_def_version", "rules_version", name="pk_metric_snapshots"
        ),
    )
    op.execute("REVOKE ALL ON TABLE metric_snapshots FROM PUBLIC")


def downgrade() -> None:
    op.drop_table("metric_snapshots")
