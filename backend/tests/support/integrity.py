"""Helpers for the corrections fingerprint tests (ST-076b; NFR-045.3; IT-05-04).

* ``audited_match``: a match with a confirmed correction and its undo, through the API.
* ``fingerprint``: ``racket.matches.public.corrections_fingerprint`` on a fresh session.
* ``restored_copy``: ``pg_dump -Fc`` of a database restored with ``pg_restore`` into a new,
  empty database beside it (ADR 0058 rule 4, step 9 in miniature); dropped on exit.
* ``plant_deleted_correction``: deletes one correction row as the table owner, with the
  append-only triggers off inside that transaction only, the "lost row" a restore must catch.
"""

from __future__ import annotations

import secrets
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from tests.support import scorebook as sb
from tests.support.api import ApiDriver


def audited_match(api: ApiDriver, user: str = "ivy") -> str:
    match_id = sb.ready_tagged_match(api, user, title="IT-05-04")
    client = api.as_user(user)
    rally_2 = api.run(sb.sheet(client, match_id)).json()["rows"][1]["rally_id"]
    version = api.run(sb.version_of(client, match_id))
    corrected = api.run(
        sb.command(client, "correct", version=version, body={"field": "ending", "value": "winner"},
                   match_id=match_id, rally_id=rally_2)
    )  # fmt: skip
    assert corrected.status_code == 200, corrected.text
    undone = api.run(sb.command(client, "undo", version=corrected.json()["version"],
                                match_id=match_id))  # fmt: skip
    assert undone.status_code == 200, undone.text
    return match_id


def fingerprint(engine: sa.Engine) -> tuple[int, str]:
    from racket.matches.public import corrections_fingerprint

    with Session(engine) as session:
        count, digest = corrections_fingerprint(session)
    return count, digest


def correction_count(engine: sa.Engine) -> int:
    with engine.connect() as conn:
        return int(conn.execute(sa.text("SELECT count(*) FROM match_corrections")).scalar_one())


def libpq_url(engine_or_url: Any) -> str:
    url = make_url(engine_or_url.url if hasattr(engine_or_url, "url") else engine_or_url)
    return url.set(drivername="postgresql").render_as_string(hide_password=False)


@contextmanager
def restored_copy(engine: sa.Engine) -> Iterator[sa.Engine]:
    source = make_url(engine.url)
    name = f"{(source.database or 'racket')[:40]}_rs{secrets.token_hex(3)}"
    admin = sa.create_engine(source, isolation_level="AUTOCOMMIT")
    target = source.set(database=name)
    copy: sa.Engine | None = None
    try:
        with admin.connect() as conn:
            conn.execute(sa.text(f'CREATE DATABASE "{name}"'))
        with tempfile.TemporaryDirectory() as tmp:
            dump = Path(tmp) / "db.dump"
            subprocess.run(["pg_dump", "-Fc", "-f", str(dump), "-d", libpq_url(source)],
                           check=True, capture_output=True, timeout=120)  # fmt: skip
            subprocess.run(["pg_restore", "--exit-on-error", "--single-transaction",
                            "-d", libpq_url(target), str(dump)],
                           check=True, capture_output=True, timeout=120)  # fmt: skip
        copy = sa.create_engine(target)
        yield copy
    finally:
        if copy is not None:
            copy.dispose()
        with admin.connect() as conn:
            conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def plant_deleted_correction(engine: sa.Engine, match_id: str) -> None:
    """Delete the newest correction row of ``match_id`` (the undo) behind the guard."""
    with engine.begin() as conn:
        conn.execute(sa.text("ALTER TABLE match_corrections DISABLE TRIGGER USER"))
        deleted = conn.execute(
            sa.text(
                "DELETE FROM match_corrections WHERE id = (SELECT id FROM match_corrections "
                "WHERE match_id = :m ORDER BY version DESC, id DESC LIMIT 1) RETURNING id"
            ),
            {"m": match_id},
        ).all()
        conn.execute(sa.text("ALTER TABLE match_corrections ENABLE TRIGGER USER"))
    assert len(deleted) == 1
