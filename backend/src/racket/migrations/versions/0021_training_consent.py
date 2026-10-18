"""FR-009 training-data consent (ST-070; api-sprint-04 §6; OQ-06, ADR 0023; SEC-4 T4-CS-1..4).

* ``training_consents``: the account's current opt-in. No row means not opted in (off by
  default, T4-CS-1). Keyed by the account only, deleted with it.
* ``training_consent_events``: one row per change (``account_id``, ``opt_in``, ``changed_at``),
  the audit trail of T4-CS-3. No IP and no user agent (data minimisation). A PUT with the
  current value writes nothing. Deleted with the account.

Grants as 0012/0013: nothing for PUBLIC, nothing for the media worker role.

Revision ID: 0021
Revises: 0020
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def _account_fk(name: str) -> sa.ForeignKey:
    return sa.ForeignKey("accounts.id", ondelete="CASCADE", name=name)


def upgrade() -> None:
    at = sa.DateTime(timezone=True)
    op.create_table(
        "training_consents",
        sa.Column(
            "account_id", sa.Uuid(), _account_fk("training_consents_account_fk"), primary_key=True
        ),
        sa.Column("opt_in", sa.Boolean(), nullable=False),
        sa.Column("changed_at", at, nullable=False),
    )
    op.create_table(
        "training_consent_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(),
            _account_fk("training_consent_events_account_fk"),
            nullable=False,
        ),
        sa.Column("opt_in", sa.Boolean(), nullable=False),
        sa.Column("changed_at", at, nullable=False),
    )
    op.create_index(
        "training_consent_events_account_idx", "training_consent_events", ["account_id"]
    )
    for table in ("training_consents", "training_consent_events"):
        op.execute(f"REVOKE ALL ON TABLE {table} FROM PUBLIC")


def downgrade() -> None:
    op.drop_table("training_consent_events")
    op.drop_table("training_consents")
