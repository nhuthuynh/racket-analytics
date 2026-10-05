"""``match_corrections`` is append-only at the database level (ST-031; FR-052; IT-02-03;
match-aggregate §3 I8, §6).

A ``BEFORE UPDATE OR DELETE`` row trigger refuses every change to an audit row, except the
delete cascaded from deleting its match (account or match deletion, Sprint 3): that delete
runs inside the foreign key's own trigger, so ``pg_trigger_depth() > 1`` (BE-D1-06). The
privileges are revoked from PUBLIC; the app role's own grants are narrowed by ST-042.

Revision ID: 0010
Revises: 0009
"""

from __future__ import annotations

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION match_corrections_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' AND pg_trigger_depth() > 1 THEN
                RETURN OLD;  -- cascaded from deleting the match
            END IF;
            RAISE EXCEPTION 'match_corrections is append-only'
                USING ERRCODE = 'insufficient_privilege';
        END
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER match_corrections_append_only BEFORE UPDATE OR DELETE "
        "ON match_corrections FOR EACH ROW EXECUTE FUNCTION match_corrections_append_only()"
    )
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON match_corrections FROM PUBLIC")


def downgrade() -> None:
    op.execute("DROP TRIGGER match_corrections_append_only ON match_corrections")
    op.execute("DROP FUNCTION match_corrections_append_only()")
