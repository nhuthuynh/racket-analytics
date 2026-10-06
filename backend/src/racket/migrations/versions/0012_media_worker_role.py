"""The media sandbox worker gets its own Postgres role with only the probe stage's grants
(ST-042; NFR-054; threat model S1-F3, v0 F-1; IT-03-10).

``racket_media_worker`` is a NOLOGIN group role: it holds the grants and nothing else. The
login that the Compose worker uses is created outside the migrations (no password in code,
AQS/SEC-06) as a member of it (SRE half of ST-042):

    CREATE ROLE <worker login> LOGIN PASSWORD '<from the secret store>' IN ROLE racket_media_worker;

Grants are exactly what ``racket.worker`` running the ``probe`` stage issues (job runtime,
``video_ingest.repository``, ``matches.public.reject_video``):

* ``jobs``: SELECT, UPDATE (claim, lease, settle; enqueue is the API's);
* ``media_assets``: SELECT, UPDATE, DELETE (probe status; a refused file's row);
* ``media_facts``: SELECT, INSERT, DELETE (facts; a refused file's rows);
* ``upload_sessions``: SELECT, DELETE (a refused file's session);
* ``matches``: SELECT, UPDATE (the refusal reason, §6.6); ``match_participants``: SELECT.

Nothing on ``accounts``, ``sessions``, ``sign_in_*``, the scorebook tables or any table added
later (no default privileges). Roles are cluster-wide, so the role is created only when absent
and is dropped on downgrade only when no other database still grants to it.

Revision ID: 0012
Revises: 0011
"""

from __future__ import annotations

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

ROLE = "racket_media_worker"
GRANTS: dict[str, tuple[str, ...]] = {
    "jobs": ("SELECT", "UPDATE"),
    "media_assets": ("SELECT", "UPDATE", "DELETE"),
    "media_facts": ("SELECT", "INSERT", "DELETE"),
    "upload_sessions": ("SELECT", "DELETE"),
    "matches": ("SELECT", "UPDATE"),
    "match_participants": ("SELECT",),
}


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'racket_media_worker') THEN
                CREATE ROLE racket_media_worker
                    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
            END IF;
        END
        $$
        """
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {ROLE}")
    for table, privileges in GRANTS.items():
        op.execute(f"GRANT {', '.join(privileges)} ON TABLE {table} TO {ROLE}")


def downgrade() -> None:
    for table in GRANTS:
        op.execute(f"REVOKE ALL ON TABLE {table} FROM {ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {ROLE}")
    op.execute(
        """
        DO $$
        BEGIN
            DROP ROLE IF EXISTS racket_media_worker;
        EXCEPTION WHEN dependent_objects_still_exist THEN
            NULL;  -- another database of this cluster still grants to the role
        END
        $$
        """
    )
