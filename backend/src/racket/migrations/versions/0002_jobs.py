"""Postgres-backed job queue (ST-007; ADR 0008 part B).

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_version", sa.String(64), nullable=False),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("failure_reason", sa.String(64), nullable=True),
        sa.Column("worker_id", sa.String(128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trace_context", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        # One job per (match_id, pipeline_version, stage): enqueue is idempotent [AQS/OPS-02].
        sa.UniqueConstraint("match_id", "pipeline_version", "stage", name="uq_jobs_key"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'done', 'failed')", name="status_known"
        ),
    )
    # Claim scans only claimable rows, oldest first.
    op.create_index(
        "ix_jobs_claimable",
        "jobs",
        ["created_at"],
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_table("jobs")
