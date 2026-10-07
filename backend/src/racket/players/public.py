"""Identity & Players' published port (context map R1 Open Host Service; deletion-and-purge.md
§3.2, §3.3, §4.2). Other contexts read accounts only through here, and only as booleans and
pseudonymous ids."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Session

from racket.platform.ratelimit import rate_limit_events
from racket.players.deletion import ERASED
from racket.players.models import accounts, sessions, sign_in_links, sign_in_requests


def lock_live_account(session: Session, account_id: uuid.UUID) -> bool:
    """SEC-S3-TM-05 (§3.3): the account row ``FOR SHARE`` until the caller commits, so an
    owned-row creation and ``DELETE /me`` run one after the other. ``False`` when the account
    is deleted (the caller answers 401 and writes nothing)."""
    found = session.execute(
        sa.select(accounts.c.id)
        .where(accounts.c.id == account_id, accounts.c.deleted_at.is_(None))
        .with_for_update(read=True)
    ).first()
    return found is not None


def lock_for_deletion(session: Session, account_id: uuid.UUID) -> bool:
    """§3.2 step 2: the account row ``FOR UPDATE``; waits for every in-flight owned-row
    creation of the account. ``False`` when it is already deleted."""
    found = session.execute(
        sa.select(accounts.c.id)
        .where(accounts.c.id == account_id, accounts.c.deleted_at.is_(None))
        .with_for_update()
    ).first()
    return found is not None


def erase_and_sign_out(session: Session, account_id: uuid.UUID, at: datetime) -> None:
    """§3.2 steps 4-6, in the caller's transaction: the unused sign-in links and requests of the
    address go first (SEC-S3-TM-06: read the address before nulling it), then the personal
    columns are nulled and every session is deleted (signed out everywhere, FR-007)."""
    row = session.execute(
        sa.select(accounts.c.email, accounts.c.email_key).where(accounts.c.id == account_id)
    ).one()
    for table in (sign_in_links, sign_in_requests):
        keys = [table.c.email_key == row.email_key] if row.email_key else []
        if row.email:
            keys.append(table.c.email == row.email)
        if keys:
            session.execute(sa.delete(table).where(sa.or_(*keys)))
    session.execute(
        sa.update(accounts).where(accounts.c.id == account_id).values(deleted_at=at, **ERASED)
    )
    session.execute(sa.delete(sessions).where(sessions.c.account_id == account_id))


def tombstoned_account_ids(session: Session, limit: int = 1000) -> list[uuid.UUID]:
    rows = session.execute(
        sa.select(accounts.c.id)
        .where(accounts.c.deleted_at.is_not(None))
        .order_by(accounts.c.deleted_at, accounts.c.id)
        .limit(limit)
    ).scalars()
    return [uuid.UUID(str(i)) for i in rows]


def claim_for_purge(session: Session, account_id: uuid.UUID) -> bool:
    found = session.execute(
        sa.select(accounts.c.id)
        .where(accounts.c.id == account_id, accounts.c.deleted_at.is_not(None))
        .with_for_update(skip_locked=True)
    ).first()
    return found is not None


def purge_account(session: Session, account_id: uuid.UUID) -> None:
    """Delete a claimed account tombstone (§4.2, after all its matches): its sessions, its
    rate-limit keys and the row."""
    session.execute(sa.delete(sessions).where(sessions.c.account_id == account_id))
    session.execute(
        sa.delete(rate_limit_events).where(rate_limit_events.c.key.like(f"%:{account_id}"))
    )
    session.execute(
        sa.delete(accounts).where(accounts.c.id == account_id, accounts.c.deleted_at.is_not(None))
    )
