"""``match_corrections`` stays append-only against a trigger-nested DELETE and TRUNCATE
(review round 2: SEC-S2-TM-01, SEC-S2-TM-02, QA-RV2-09; FR-052; IT-02-03; threat model
T-SB-6, T-SB-7).

* SEC-S2-TM-01: 0010 let every DELETE with ``pg_trigger_depth() > 1`` through. A delete is now
  allowed only when the audit row's match no longer exists, which is the foreign-key cascade
  from deleting the match. ``public.matches`` is schema-qualified and the function's
  ``search_path`` is pinned, so a temporary table named ``matches`` cannot stand in for it.
* SEC-S2-TM-02: the app role owns the table, so ``REVOKE … FROM PUBLIC`` does not stop its
  TRUNCATE and no row trigger fires on one. A ``BEFORE TRUNCATE`` statement trigger refuses it.

The owner can still drop or disable these triggers; separating the owner from the runtime role
is ST-042 (BE + SRE).

Revision ID: 0011
Revises: 0010
"""

from __future__ import annotations

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION match_corrections_append_only() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
        BEGIN
            IF TG_OP = 'DELETE' AND pg_trigger_depth() > 1
               AND NOT EXISTS (SELECT 1 FROM public.matches WHERE id = OLD.match_id) THEN
                RETURN OLD;  -- cascaded from deleting the match
            END IF;
            RAISE EXCEPTION 'match_corrections is append-only'
                USING ERRCODE = 'insufficient_privilege';
        END
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION match_corrections_no_truncate() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
        BEGIN
            RAISE EXCEPTION 'match_corrections is append-only'
                USING ERRCODE = 'insufficient_privilege';
        END
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER match_corrections_no_truncate BEFORE TRUNCATE ON match_corrections "
        "FOR EACH STATEMENT EXECUTE FUNCTION match_corrections_no_truncate()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER match_corrections_no_truncate ON match_corrections")
    op.execute("DROP FUNCTION match_corrections_no_truncate()")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION match_corrections_append_only() RETURNS trigger
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
