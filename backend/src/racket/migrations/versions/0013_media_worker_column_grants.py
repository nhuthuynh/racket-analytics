"""The media sandbox worker updates only the columns the probe stage writes (SEC-R1S3-01;
ST-042; NFR-051, NFR-054; ASVS 8.2.x, 8.3.1; IT-03-10b).

0012 granted ``UPDATE`` on all of ``matches`` and ``media_assets``, so a compromised worker could
rewrite ``owner_id`` or ``object_key`` and get past the ``WHERE id = :id AND owner_id = :me``
control. The probe stage writes only:

* ``matches``: ``status``, ``media_asset_id``, ``rejection_code``, ``rejected_at``,
  ``updated_at`` (``Match.reject_video``; the ORM updates only changed columns). ``SELECT ...
  FOR UPDATE`` needs UPDATE on at least one column, which this keeps;
* ``media_assets``: ``probe_status``, ``updated_at`` (``MediaRepository.set_probe_status``).

``match_participants`` keeps SELECT: ``MatchRepository.get_owned`` loads the aggregate's
participants on the refusal path (``matches.public.reject_video``).

Revision ID: 0013
Revises: 0012
"""

from __future__ import annotations

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

ROLE = "racket_media_worker"
COLUMN_UPDATES: dict[str, tuple[str, ...]] = {
    "matches": ("status", "media_asset_id", "rejection_code", "rejected_at", "updated_at"),
    "media_assets": ("probe_status", "updated_at"),
}


def upgrade() -> None:
    for table, columns in COLUMN_UPDATES.items():
        op.execute(f"REVOKE UPDATE ON TABLE {table} FROM {ROLE}")
        op.execute(f"GRANT UPDATE ({', '.join(columns)}) ON TABLE {table} TO {ROLE}")


def downgrade() -> None:
    for table, columns in COLUMN_UPDATES.items():
        op.execute(f"REVOKE UPDATE ({', '.join(columns)}) ON TABLE {table} FROM {ROLE}")
        op.execute(f"GRANT UPDATE ON TABLE {table} TO {ROLE}")
