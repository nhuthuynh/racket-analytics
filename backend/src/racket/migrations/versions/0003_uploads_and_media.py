"""tus upload sessions, media assets and media facts (ST-008, ST-009; ADR 0011).

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "upload_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        # Sprint 0 allows one upload per match (api-sprint-00 §6.2, 409 otherwise).
        sa.Column("match_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("length", sa.BigInteger(), nullable=False),
        sa.Column("offset", sa.BigInteger(), nullable=False),
        sa.Column("object_key", sa.String(128), nullable=False, unique=True),
        sa.Column("s3_upload_id", sa.String(1024), nullable=False),
        sa.Column("parts", JSONB(), nullable=False, server_default="[]"),
        sa.Column("staged", JSONB(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('"offset" >= 0 AND "offset" <= length', name="offset_in_range"),
    )
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("object_key", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("probe_status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "media_facts",
        # Exactly one set of facts per media asset: a re-run cannot duplicate them (IT-00-04).
        sa.Column(
            "media_asset_id",
            sa.Uuid(),
            sa.ForeignKey("media_assets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("match_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("container", sa.String(128), nullable=True),
        sa.Column("video_codec", sa.String(64), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("fps", sa.Numeric(10, 3), nullable=True),
        sa.Column("vfr", sa.Boolean(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("has_audio", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("media_facts")
    op.drop_table("media_assets")
    op.drop_table("upload_sessions")
