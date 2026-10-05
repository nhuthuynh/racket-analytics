"""The scored side of the ``Match`` aggregate: games, rallies (outcome inputs only) and the
change trail (ST-026; match-aggregate §6; FR-049, NFR-075).

No table has a score column: the score sheet is a projection (FR-049). ``matches.version`` is
the optimistic lock of every scorebook command (IT-02-04). The append-only guard on
``match_corrections`` (trigger and REVOKE, IT-02-03) comes with ST-031.

Revision ID: 0009
Revises: 0008
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

SIDE = "IN ('A', 'B')"


def _match_fk() -> sa.ForeignKey:
    return sa.ForeignKey("matches.id", ondelete="CASCADE")


def upgrade() -> None:
    op.add_column("matches", sa.Column("best_of", sa.SmallInteger(), nullable=False,
                                       server_default="3"))  # fmt: skip
    op.add_column("matches", sa.Column("version", sa.Integer(), nullable=False,
                                       server_default="0"))  # fmt: skip
    op.create_check_constraint("best_of_known", "matches", "best_of IN (1, 3)")
    op.create_check_constraint("version_not_negative", "matches", "version >= 0")

    op.create_table(
        "match_games",
        sa.Column("match_id", sa.Uuid(), _match_fk(), nullable=False),
        sa.Column("number", sa.SmallInteger(), nullable=False),
        sa.Column("first_serving_side", sa.String(1), nullable=False),
        sa.Column("ends_switched", sa.Boolean(), nullable=False),
        sa.Column("created_version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("match_id", "number", name="pk_match_games"),
        sa.CheckConstraint("number BETWEEN 1 AND 3", name="number_in_range"),
        sa.CheckConstraint(f"first_serving_side {SIDE}", name="side_known"),
    )
    op.create_table(
        "match_rallies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("match_id", sa.Uuid(), _match_fk(), nullable=False),
        sa.Column("game_number", sa.SmallInteger(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("start_ms", sa.BigInteger(), nullable=False),
        sa.Column("end_ms", sa.BigInteger(), nullable=False),
        sa.Column("ending", sa.String(16), nullable=False),
        sa.Column("winning_side", sa.String(1), nullable=True),
        sa.Column("responsible_player", sa.String(2), nullable=True),
        sa.Column("fault_kind", sa.String(16), nullable=True),
        sa.Column("withdrawn", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("match_id", "seq", name="uq_match_rallies_match_id_seq"),
        # Mirrors of I5 and I6 (match-aggregate §3), defence in depth.
        sa.CheckConstraint("start_ms >= 0 AND end_ms > start_ms", name="times_ordered"),
        sa.CheckConstraint(
            "ending IN ('winner', 'unforced_error', 'forced_error', 'fault', 'replay')",
            name="ending_known",
        ),
        sa.CheckConstraint(
            f"(ending = 'replay' AND winning_side IS NULL) OR "
            f"(ending <> 'replay' AND winning_side {SIDE})",
            name="side_matches_ending",
        ),
        sa.CheckConstraint(
            "responsible_player IS NULL OR responsible_player IN ('A1', 'A2', 'B1', 'B2')",
            name="player_known",
        ),
        sa.CheckConstraint("fault_kind IS NULL OR ending = 'fault'", name="fault_kind_only_fault"),
    )
    op.create_index("ix_match_rallies_match_id", "match_rallies", ["match_id"])
    op.create_table(
        "match_corrections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("match_id", sa.Uuid(), _match_fk(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rally_id", sa.Uuid(), nullable=True),
        sa.Column("game_number", sa.SmallInteger(), nullable=True),
        sa.Column("field", sa.String(32), nullable=True),
        # Tag fields only (sides, slots, enums, integers): no names, no free text (IT-02-09).
        sa.Column("old_value", JSONB(), nullable=True),
        sa.Column("new_value", JSONB(), nullable=True),
        sa.Column("undoes", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "kind IN ('game_started', 'correction', 'withdrawal', 'undo', 'resolution')",
            name="kind_known",
        ),
    )
    op.create_index("ix_match_corrections_match_id", "match_corrections", ["match_id"])


def downgrade() -> None:
    op.drop_table("match_corrections")
    op.drop_table("match_rallies")
    op.drop_table("match_games")
    op.drop_constraint("version_not_negative", "matches", type_="check")
    op.drop_constraint("best_of_known", "matches", type_="check")
    op.drop_column("matches", "version")
    op.drop_column("matches", "best_of")
