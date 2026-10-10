"""Dataset & Labelling's published port for the purge job (deletion-and-purge.md §2, §4.2)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from racket.dataset.repository import LabelRepository


def purge_match(session: Session, match_id: uuid.UUID) -> int:
    """Delete the match's consent record and label session (caller's transaction)."""
    return LabelRepository(session).delete_for_match(match_id)
