"""Migrate databases of one Postgres cluster the way parallel test workers do (CI-INTEG-BUDGET).

Run with the backend's interpreter, never imported by infra tests (they have no ``racket``):

    uv run --locked python parallel_migrate.py step    BASE_URL ROLE MODULE
    uv run --locked python parallel_migrate.py workers BASE_URL ROLE N

Both add one fixture revision on top of the real migration chain. It creates the cluster-wide
role ROLE with the check-then-create pattern of migration 0012 (``racket_media_worker``), with a
1 s pause between the check and the create, so workers that migrate at the same moment always
overlap (the race is deterministic, not 4-in-5 as measured with 0012 itself).

* ``step``: runs ``python -m MODULE`` (the integration job's migrate step) on BASE_URL.
* ``workers``: N processes each create their own database beside BASE_URL's, migrate it to the
  real head, wait for each other, then apply the fixture revision at the same moment. Every
  database is dropped at the end.

Prints one JSON line with the outcome.
"""

from __future__ import annotations

import contextlib
import json
import multiprocessing as mp
import os
import runpy
import secrets
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import racket.platform.db as db
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

REVISION = "ci_cluster_role"
TEMPLATE = '''"""Fixture: a cluster-wide role, created as migration 0012 does (CI-INTEG-BUDGET)."""
from alembic import op

revision = "{revision}"
down_revision = "{down}"


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                PERFORM pg_sleep(1);
                CREATE ROLE {role} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
            END IF;
        END
        $$
    """)


def downgrade() -> None:
    pass
'''


def real_head() -> str:
    config = Config()
    config.set_main_option("script_location", str(db.MIGRATIONS_DIR))
    head = ScriptDirectory.from_config(config).get_current_head()
    assert head, "the migration chain has no head"
    return head


def with_fixture_revision(role: str) -> Path:
    """A copy of the real migrations with the cluster-role revision on top."""
    copy = Path(tempfile.mkdtemp(prefix="ra-migrations-")) / "migrations"
    shutil.copytree(db.MIGRATIONS_DIR, copy, ignore=shutil.ignore_patterns("__pycache__"))
    body = TEMPLATE.format(revision=REVISION, down=real_head(), role=role)
    (copy / "versions" / f"{REVISION}.py").write_text(body, encoding="utf-8")
    return copy


def version_of(url: str) -> str | None:
    engine = create_engine(db.sqlalchemy_url(url))
    try:
        with engine.connect() as conn:
            return conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    finally:
        engine.dispose()


def _admin(base_url: str) -> Any:
    return create_engine(db.sqlalchemy_url(base_url), isolation_level="AUTOCOMMIT")


# ---------------------------------------------------------------- step
def step(base_url: str, role: str, module: str) -> dict[str, Any]:
    db.MIGRATIONS_DIR = with_fixture_revision(role)
    os.environ["DATABASE_URL"] = base_url
    try:
        runpy.run_module(module, run_name="__main__")
        rc: int | str | None = 0
    except SystemExit as exc:
        rc = exc.code
    return {"rc": rc, "base_version": version_of(base_url)}


# ---------------------------------------------------------------- workers
def _worker(args: tuple[str, str, Any]) -> str | None:
    url, fixture_dir, barrier = args
    try:
        db.upgrade_to_head(url)  # the real chain first, at each worker's own pace
        barrier.wait(timeout=300)
        db.MIGRATIONS_DIR = Path(fixture_dir)
        db.upgrade_to_head(url)  # every worker reaches the cluster role at the same moment
    except Exception as exc:  # noqa: BLE001 - reported to the test
        return f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
    return None


def workers(base_url: str, role: str, n: int) -> dict[str, Any]:
    base = make_url(db.sqlalchemy_url(base_url))
    fixture_dir = with_fixture_revision(role)
    names = [f"{base.database}_pm{os.getpid()}_{i}_{secrets.token_hex(2)}" for i in range(n)]
    urls = [base.set(database=name).render_as_string(hide_password=False) for name in names]
    admin = _admin(base_url)
    try:
        with admin.connect() as conn:
            for name in names:
                conn.execute(text(f'CREATE DATABASE "{name}"'))
        ctx = mp.get_context("spawn")
        with ctx.Manager() as manager:
            barrier = manager.Barrier(n)
            with ctx.Pool(n) as pool:
                outcomes = pool.map(_worker, [(u, str(fixture_dir), barrier) for u in urls])
        failed = [o for o in outcomes if o]
        at_head = sum(1 for u in urls if version_of(u) == REVISION)
    finally:
        with admin.connect() as conn:
            for name in names:
                with contextlib.suppress(Exception):
                    conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()
    return {"workers": n, "failed": failed, "at_head": at_head}


def main(argv: list[str]) -> int:
    if len(argv) != 5 or argv[1] not in {"step", "workers"}:
        print(__doc__, file=sys.stderr)
        return 2
    mode, base_url, role, last = argv[1:]
    out = step(base_url, role, last) if mode == "step" else workers(base_url, role, int(last))
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
