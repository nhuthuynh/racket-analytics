"""Coaching's published port (coaching-plan §1, §8; context-map rule 1).

``purge_account`` is called by the purge job before the account row and ``purge_match`` before
the match row (ADR 0042 order). Coaching stores rows only, no object.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from racket.coaching.plan import repository


def purge_account(session: Session, account_id: uuid.UUID) -> int:
    """Delete every training-plan row of ``account_id``; the number of rows deleted."""
    return repository.delete_owned(session, account_id)


def purge_match(session: Session, match_id: uuid.UUID) -> int:
    """Mark every plan built from ``match_id`` stale and delete each plan row naming it
    (coaching-plan §8; T4-PL-9); the number of rows deleted."""
    return repository.purge_match(session, match_id)
