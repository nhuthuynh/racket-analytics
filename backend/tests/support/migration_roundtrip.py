"""Migration round trip (ST-082; REL-1.3; ADR 0058 rule 7 "Every migration is reversible").

``missing_downgrades`` reads each migration module and names the revisions whose ``downgrade``
is absent or does nothing. ``round_trip`` walks a seeded scratch database from the head down to
the base, one revision at a time, and at each revision steps it down and up again, comparing the
schema and the row counts of the tables that outlived the downgrade.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, create_engine, text

from racket.platform.db import MIGRATIONS_DIR, sqlalchemy_url
from tests.support.db import create_session_database, drop_session_database


def _is_noop(body: list[ast.stmt]) -> bool:
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            continue  # a docstring or `...`
        if isinstance(stmt, ast.Raise):
            continue  # raise NotImplementedError: a one-way migration
        return False
    return True


def missing_downgrades(versions_dir: Path) -> list[str]:
    """Revision ids (sorted) whose module has no ``downgrade()`` or one that does nothing."""
    missing = []
    for path in sorted(versions_dir.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        revision = path.stem
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "revision" for t in node.targets
            ):
                if isinstance(node.value, ast.Constant):
                    revision = str(node.value.value)
        down = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "downgrade"]
        if not down or _is_noop(down[0].body):
            missing.append(revision)
    return sorted(missing)


def revisions(script_location: Path = MIGRATIONS_DIR) -> list[tuple[str, str | None]]:
    """(revision, down_revision) pairs from the head down to the base."""
    config = Config()
    config.set_main_option("script_location", str(script_location))
    script = ScriptDirectory.from_config(config)
    out: list[tuple[str, str | None]] = []
    for rev in script.walk_revisions():
        down = rev.down_revision
        out.append((rev.revision, down if isinstance(down, str) or down is None else down[0]))
    return out


def migrate(url: str, target: str, *, down: bool = False) -> None:
    """``alembic upgrade|downgrade <target>`` on ``url``, committed (as ``upgrade_to_head``)."""
    engine = create_engine(sqlalchemy_url(url))
    try:
        with engine.begin() as connection:
            config = Config()
            config.set_main_option("script_location", str(MIGRATIONS_DIR))
            config.attributes["connection"] = connection
            (command.downgrade if down else command.upgrade)(config, target)
    finally:
        engine.dispose()


@contextmanager
def scratch_database(base_url: str) -> Iterator[str]:
    """A fresh, empty database beside ``base_url``'s, dropped afterwards."""
    url = create_session_database(base_url)
    try:
        yield url
    finally:
        drop_session_database(url, base_url)


SCHEMA = text(
    "SELECT table_name, column_name, data_type, is_nullable, coalesce(column_default, '') "
    "FROM information_schema.columns WHERE table_schema = current_schema() "
    "UNION ALL SELECT tablename, indexname, 'index', '', indexdef FROM pg_indexes "
    "WHERE schemaname = current_schema() "
    "UNION ALL SELECT conrelid::regclass::text, conname, 'constraint', '', "
    "pg_get_constraintdef(oid) FROM pg_constraint "
    "WHERE connamespace = current_schema()::regnamespace"
)


def schema(conn: Connection) -> frozenset[tuple[str, ...]]:
    return frozenset(tuple(str(c) for c in row) for row in conn.execute(SCHEMA))


def row_counts(conn: Connection) -> dict[str, int]:
    tables = conn.execute(
        text(
            "SELECT tablename FROM pg_tables WHERE schemaname = current_schema() "
            "AND tablename <> 'alembic_version'"
        )
    ).scalars()
    return {t: conn.execute(text(f'SELECT count(*) FROM "{t}"')).scalar_one() for t in tables}


def current_revision(conn: Connection) -> str | None:
    return conn.execute(text("SELECT version_num FROM alembic_version")).scalar()


SEED = (
    # A magic-link account (no username, the R1 sign-in) and a dev-identity one (a username).
    "INSERT INTO accounts (id, created_at, email, email_key, display_name) VALUES "
    "('00000000-0000-4000-8000-000000000001', now(), 'seed@example.test', 'seed-key', 'Seed')",
    "INSERT INTO accounts (id, created_at, username, email_key) VALUES "
    "('00000000-0000-4000-8000-000000000002', now(), 'dev-user', 'dev-key')",
    "INSERT INTO matches (id, owner_id, title, format, status, created_at, updated_at) VALUES "
    "('00000000-0000-4000-8000-0000000000a1', '00000000-0000-4000-8000-000000000001', "
    "'Seed match', 'doubles', 'created', now(), now())",
    "INSERT INTO match_participants (match_id, slot, nickname, is_me) VALUES "
    "('00000000-0000-4000-8000-0000000000a1', 'A1', 'Me', true), "
    "('00000000-0000-4000-8000-0000000000a1', 'A2', 'Pat', false), "
    "('00000000-0000-4000-8000-0000000000a1', 'B1', 'Sam', false), "
    "('00000000-0000-4000-8000-0000000000a1', 'B2', 'Lee', false)",
    "INSERT INTO match_games (match_id, number, first_serving_side, ends_switched, "
    "created_version) VALUES ('00000000-0000-4000-8000-0000000000a1', 1, 'A', false, 1)",
)


def seed(url: str) -> None:
    """Two accounts; the first owns one doubles match, its four players and its first game."""
    engine = create_engine(sqlalchemy_url(url))
    try:
        with engine.begin() as conn:
            for statement in SEED:
                conn.execute(text(statement))
    finally:
        engine.dispose()


@dataclass(frozen=True)
class Step:
    revision: str
    back_at: str | None
    schema_equal: bool
    lost_rows: dict[str, tuple[int, int]]  # table -> (before, after), outlived tables only


def round_trip(url: str) -> list[Step]:
    """From the head down: at each revision step down one and up again, then step down."""
    engine = create_engine(sqlalchemy_url(url))
    steps = []
    try:
        for revision, previous in revisions():
            with engine.connect() as conn:
                before_schema, before_rows = schema(conn), row_counts(conn)
            migrate(url, previous or "base", down=True)
            with engine.connect() as conn:
                outlived = set(row_counts(conn))
            migrate(url, revision)
            with engine.connect() as conn:
                after_rows = row_counts(conn)
                lost = {
                    t: (before_rows[t], after_rows.get(t, 0))
                    for t in outlived
                    if before_rows.get(t, 0) != after_rows.get(t, 0)
                }
                steps.append(Step(revision, current_revision(conn), schema(conn) == before_schema, lost))
            migrate(url, previous or "base", down=True)
    finally:
        engine.dispose()
    return steps
