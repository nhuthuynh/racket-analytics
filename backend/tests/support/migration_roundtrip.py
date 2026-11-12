"""Migration round trip (ST-082; REL-1.3; ADR 0058 rule 7 "Every migration is reversible").

``missing_downgrades`` reads each migration module and names the revisions whose ``downgrade``
is absent or does nothing. ``round_trip`` walks a seeded scratch database from the head down to
the base, one revision at a time, and at each revision steps it down and up again, comparing the
schema and the row counts of the tables that outlived the downgrade. ``data_dependent_tables``
names the tables a downgrade changes but keeps; the seed has a row in each of them.

Row counts only: a value lost when a column is dropped and added again is not detected. Under
ADR 0058 rule 7's expand/contract rule a release never drops a column its predecessor reads, so
this is accepted for R1 (judgment; PE F3 on PR #224).
"""

from __future__ import annotations

import ast
import re
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
            named = isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "revision" for t in node.targets
            )
            if named and isinstance(node.value, ast.Constant):
                revision = str(node.value.value)
        down = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "downgrade"]
        if not down or _is_noop(down[0].body):
            missing.append(revision)
    return sorted(missing)


# op.<call> -> index of its table argument, for the calls that change a table that outlives them.
TABLE_ARG = {
    "add_column": 0,
    "drop_column": 0,
    "alter_column": 0,
    "drop_constraint": 1,
    "create_unique_constraint": 1,
    "create_check_constraint": 1,
    "create_foreign_key": 1,
    "create_index": 1,
    "drop_index": 1,
}


def data_dependent_tables(versions_dir: Path) -> set[str]:
    """Tables whose columns, indexes or constraints a ``downgrade()`` changes and outlive it."""
    tables: set[str] = set()
    for path in sorted(versions_dir.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for fn in tree.body:
            if not (isinstance(fn, ast.FunctionDef) and fn.name == "downgrade"):
                continue
            changed, dropped = set(), set()
            for node in ast.walk(fn):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                    continue
                name, args = node.func.attr, node.args
                if name == "drop_table" and args and isinstance(args[0], ast.Constant):
                    dropped.add(str(args[0].value))
                index = TABLE_ARG.get(name)
                if index is not None and len(args) > index:
                    arg = args[index]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        changed.add(arg.value)
            tables |= changed - dropped
    return tables


def seeded_tables(statements: tuple[str, ...]) -> set[str]:
    """The ``INSERT INTO`` targets of ``statements``."""
    return {m.group(1) for s in statements if (m := INSERT.match(s))}


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


INSERT = re.compile(r"\s*insert\s+into\s+(\w+)", re.IGNORECASE)


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
    # Tables whose columns or indexes a later downgrade changes (0005, 0006, 0008; PE F3, PR #224).
    'INSERT INTO upload_sessions (id, owner_id, match_id, length, "offset", object_key, '
    "s3_upload_id, status, created_at, updated_at, expires_at) VALUES "
    "('00000000-0000-4000-8000-0000000000b1', '00000000-0000-4000-8000-000000000001', "
    "'00000000-0000-4000-8000-0000000000a1', 10, 0, 'seed/object', 'seed-upload', 'open', "
    "now(), now(), now() + interval '1 day')",
    "INSERT INTO sign_in_links (token_sha256, email_key, email, created_at, expires_at) VALUES "
    "('seed-token-sha256', 'seed-key', 'seed@example.test', now(), now() + interval '15 minutes')",
    "INSERT INTO sessions (token_sha256, account_id, created_at, expires_at, last_seen_at) "
    "VALUES ('seed-session-sha256', '00000000-0000-4000-8000-000000000001', now(), "
    "now() + interval '30 days', now())",
    # The scorebook rows of 0009, whose triggers 0010 and 0011 drop and add again.
    "INSERT INTO match_rallies (id, match_id, game_number, seq, start_ms, end_ms, ending, "
    "winning_side, created_version) VALUES ('00000000-0000-4000-8000-0000000000c1', "
    "'00000000-0000-4000-8000-0000000000a1', 1, 1, 0, 4000, 'winner', 'A', 2)",
    "INSERT INTO match_corrections (id, match_id, version, kind, actor_id, at, game_number) "
    "VALUES ('00000000-0000-4000-8000-0000000000d1', '00000000-0000-4000-8000-0000000000a1', 1, "
    "'game_started', '00000000-0000-4000-8000-000000000001', now(), 1)",
)


def seed(url: str) -> None:
    """Two accounts; the first owns one doubles match with its four players, its first game, a
    rally, a correction, an upload session and a session, plus one sign-in link."""
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
                steps.append(
                    Step(revision, current_revision(conn), schema(conn) == before_schema, lost)
                )
            migrate(url, previous or "base", down=True)
    finally:
        engine.dispose()
    return steps
