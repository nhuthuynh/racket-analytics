"""Coaching's published port (coaching-plan §1, §8; context-map rule 1).

``purge_account`` is called by the purge job before the account row (ADR 0042 order). Coaching
stores rows only, no object.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from racket.coaching.plan.repository import delete_owned


def purge_account(session: Session, account_id: uuid.UUID) -> int:
    """Delete every training-plan row of ``account_id``; the number of rows deleted."""
    return delete_owned(session, account_id)
