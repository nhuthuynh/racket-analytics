"""Training plans (ST-061a; coaching-plan §5, §8, §9; FR-121, FR-124; NFR-051, NFR-066 b).

Coaching's tables. One plan per account (``training_plans.owner_id`` unique); every plan,
session and assignment row carries ``owner_id`` so each query filters by owner and the purge
inventory (``owner_id``/``account_id``/``match_id`` columns) sees every row. No foreign key to
``accounts`` or ``matches`` (context-map rule 1): ``racket.coaching.public.purge_account`` deletes
the rows before the account row (ADR 0042 order). Inside the context the children cascade from
their plan.

* ``training_plans``: ``version`` (optimistic concurrency), ``library_version``,
  ``preferences``/``weaknesses``/``unfitted``/``excluded_drills`` (JSON), ``limited_data``,
  ``stale`` (a cited match was deleted), ``content_digest``.
* ``plan_sessions`` (week, index, budget, ``done_at``), ``plan_assignments`` (drill ref, minutes,
  weakness, citation columns for ST-057, ``reason_not_for_me`` for ST-062),
  ``plan_citation_rallies``, ``plan_source_matches``.
* ``plan_done_ops``: the idempotent done ops, unique ``(account_id, op_id)`` (api-sprint-04 §3.3).

Grants as 0012/0013: nothing for PUBLIC, nothing for the media worker role.

Revision ID: 0018
Revises: 0017
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

TABLES = (
    "training_plans",
    "plan_sessions",
    "plan_assignments",
    "plan_citation_rallies",
    "plan_source_matches",
    "plan_done_ops",
)


def _parent(column: str, target: str, name: str) -> sa.Column:
    return sa.Column(
        column, sa.Uuid(), sa.ForeignKey(target, ondelete="CASCADE", name=name), nullable=False
    )


def upgrade() -> None:
    at = sa.DateTime(timezone=True)
    op.create_table(
        "training_plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("library_version", sa.String(128), nullable=False),
        sa.Column("preferences", JSONB(), nullable=False),
        sa.Column("weaknesses", JSONB(), nullable=False),
        sa.Column("unfitted", JSONB(), nullable=False),
        sa.Column("excluded_drills", JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("limited_data", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("content_digest", sa.String(80), nullable=False),
        sa.Column("created_at", at, nullable=False),
        sa.Column("updated_at", at, nullable=False),
        sa.UniqueConstraint("owner_id", name="uq_training_plans_owner_id"),
        sa.CheckConstraint("version >= 1", name="ck_training_plans_version"),
    )
    op.create_table(
        "plan_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _parent("plan_id", "training_plans.id", "fk_plan_sessions_plan_id"),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("week", sa.SmallInteger(), nullable=False),
        sa.Column("session_index", sa.SmallInteger(), nullable=False),
        sa.Column("minutes_budget", sa.SmallInteger(), nullable=False),
        sa.Column("done_at", at, nullable=True),
        sa.UniqueConstraint("plan_id", "week", "session_index", name="uq_plan_sessions_slot"),
    )
    op.create_index("ix_plan_sessions_owner_id", "plan_sessions", ["owner_id"])
    op.create_table(
        "plan_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _parent("session_id", "plan_sessions.id", "fk_plan_assignments_session_id"),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("drill_ref", sa.String(160), nullable=False),
        sa.Column("minutes", sa.SmallInteger(), nullable=False),
        sa.Column("weakness_id", sa.String(64), nullable=True),
        sa.Column("metric_id", sa.String(64), nullable=True),
        sa.Column("metric_version", sa.Integer(), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("n", sa.Integer(), nullable=True),
        sa.Column("k", sa.Integer(), nullable=True),
        sa.Column("low_sample", sa.Boolean(), nullable=True),
        sa.Column("reason_not_for_me", sa.String(200), nullable=True),
        sa.UniqueConstraint("session_id", "position", name="uq_plan_assignments_position"),
    )
    op.create_index("ix_plan_assignments_owner_id", "plan_assignments", ["owner_id"])
    op.create_table(
        "plan_citation_rallies",
        _parent("assignment_id", "plan_assignments.id", "fk_plan_citation_rallies_assignment_id"),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("rally_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("assignment_id", "position", name="pk_plan_citation_rallies"),
    )
    op.create_index("ix_plan_citation_rallies_match_id", "plan_citation_rallies", ["match_id"])
    op.create_table(
        "plan_source_matches",
        _parent("plan_id", "training_plans.id", "fk_plan_source_matches_plan_id"),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("plan_id", "match_id", name="pk_plan_source_matches"),
    )
    op.create_index("ix_plan_source_matches_match_id", "plan_source_matches", ["match_id"])
    op.create_table(
        "plan_done_ops",
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("op_id", sa.String(64), nullable=False),
        _parent("session_id", "plan_sessions.id", "fk_plan_done_ops_session_id"),
        sa.Column("plan_version", sa.Integer(), nullable=False),
        sa.Column("created_at", at, nullable=False),
        sa.PrimaryKeyConstraint("account_id", "op_id", name="pk_plan_done_ops"),
    )
    for table in TABLES:
        op.execute(f"REVOKE ALL ON TABLE {table} FROM PUBLIC")


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
