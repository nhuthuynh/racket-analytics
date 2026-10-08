"""Full Tag persistence (ST-052b; api-sprint-03 §5; FR-150, FR-151).

* ``account_roles`` (Identity & Players): the labeller role. Deleted with its account (FK
  cascade, the purge's ``purge_account``).
* ``label_consents`` and ``label_sessions`` (Dataset & Labelling): the team-held consent record
  and the label session of a match. No foreign key to ``matches`` (context-map rule 1); the
  purge removes them through ``dataset.public.purge_match``.

The media worker role gets nothing on any of them (ST-042).

Revision ID: 0017
Revises: 0016
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_roles",
        sa.Column(
            "account_id",
            sa.Uuid(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE", name="fk_account_roles_account_id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("account_id", "role", name="pk_account_roles"),
    )
    op.create_table(
        "label_consents",
        sa.Column("match_id", sa.Uuid(), primary_key=True),
        sa.Column("reference", sa.String(64), nullable=False),
        sa.Column("recorded_by", sa.String(64), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "label_sessions",
        sa.Column("match_id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("rallies", JSONB(), nullable=False),
        sa.Column("events", JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for table in ("account_roles", "label_consents", "label_sessions"):
        op.execute(f"REVOKE ALL ON TABLE {table} FROM PUBLIC")


def downgrade() -> None:
    for table in ("label_sessions", "label_consents", "account_roles"):
        op.drop_table(table)
