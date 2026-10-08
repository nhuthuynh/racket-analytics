"""IT-03-10 (ST-042; NFR-054; threat model S1-F3, v0 F-1): the media sandbox worker's own
Postgres role cannot read identity data and can do exactly the probe stage's work.

sprint-03 §5 TDD order: 1. worker role SELECT on ``sessions`` -> permission denied; 2. on
``accounts`` -> denied; 3. on the job table -> allowed. Then the real in-process worker runs the
probe stage connected as that role (``options=-c role=...``, as Compose's worker login does):
a valid clip is probed, an over-long clip is refused and its rows deleted, a malformed file
ends ``probe_failed``. Each refusal has a positive control (testing-strategy rule 8).
Real Postgres and object store.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import quote

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ProgrammingError

from tests.support import contract, media, tus_ext
from tests.support.api import ApiDriver
from tests.support.db import database_url
from tests.support.flows import create_match
from tests.support.worker import media_facts_count

WORKER_ROLE = "racket_media_worker"

IDENTITY_TABLES = ("sessions", "accounts", "sign_in_links", "sign_in_requests")
OTHER_PRIVATE = ("match_rallies", "match_corrections", "match_games", "rate_limit_events")
WORKER_READS = (
    "jobs",
    "media_assets",
    "media_facts",
    "upload_sessions",
    "matches",
    "match_participants",
)


@contextmanager
def as_worker(engine: Any) -> Iterator[Any]:
    with engine.connect() as conn:
        tx = conn.begin()
        try:
            conn.execute(sa.text(f"SET LOCAL ROLE {WORKER_ROLE}"))
            yield conn
        finally:
            tx.rollback()


def _denied(engine: Any, statement: str) -> None:
    with pytest.raises(ProgrammingError, match="permission denied"), as_worker(engine) as conn:
        conn.execute(sa.text(statement))


# ---------------------------------------------------------------- 1, 2: identity data refused
@pytest.mark.parametrize("table", IDENTITY_TABLES)
def test_it_03_10_the_worker_role_cannot_read_identity_tables(db_engine: Any, table: str) -> None:
    _denied(db_engine, f"SELECT 1 FROM {table} LIMIT 1")


@pytest.mark.parametrize("table", OTHER_PRIVATE)
def test_it_03_10_the_worker_role_cannot_read_tables_the_probe_never_uses(
    db_engine: Any, table: str
) -> None:
    _denied(db_engine, f"SELECT 1 FROM {table} LIMIT 1")


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO jobs (id) VALUES (gen_random_uuid())",
        "DELETE FROM jobs",
        "DELETE FROM matches",
        "UPDATE accounts SET email = NULL",
        "INSERT INTO matches (id) VALUES (gen_random_uuid())",
        "TRUNCATE media_facts",
        "CREATE TABLE worker_owned (id int)",
    ],
    ids=["insert-job", "delete-job", "delete-match", "update-account", "insert-match",
         "truncate", "create-table"],
)  # fmt: skip
def test_it_03_10_the_worker_role_cannot_write_beyond_the_probe(
    db_engine: Any, statement: str
) -> None:
    _denied(db_engine, statement)


# ---------------------------------------------------------------- 3: positive controls
@pytest.mark.parametrize("table", WORKER_READS)
def test_it_03_10_the_worker_role_reads_the_tables_the_probe_uses(
    db_engine: Any, table: str
) -> None:
    with as_worker(db_engine) as conn:
        assert conn.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one() >= 0


def test_it_03_10_the_worker_role_updates_jobs(db_engine: Any) -> None:
    with as_worker(db_engine) as conn:
        conn.execute(sa.text("UPDATE jobs SET attempts = attempts WHERE false"))


def test_it_03_10_the_role_cannot_log_in() -> None:
    url = make_url(database_url())
    engine = sa.create_engine(
        url.set(drivername="postgresql+psycopg", username=WORKER_ROLE, password="x")
    )
    with pytest.raises(sa.exc.OperationalError):
        engine.connect().close()
    engine.dispose()


# ---------------------------------------------------------------- the real worker, as the role
@pytest.fixture
def worker_env(monkeypatch: pytest.MonkeyPatch) -> None:
    url = make_url(database_url())
    options = quote(f"-c role={WORKER_ROLE}")
    rendered = url.render_as_string(hide_password=False)
    joiner = "&" if "?" in rendered else "?"
    monkeypatch.setenv("DATABASE_URL", f"{rendered}{joiner}options={options}")


def _send(api: ApiDriver, data: bytes, title: str) -> str:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, title))
    upload = api.run(tus_ext.start(ivy, match_id, data, filename="match.mp4"))
    assert api.run(tus_ext.patch(ivy, upload, 0, data)).status_code == 204
    return str(match_id)


def _status(api: ApiDriver, match_id: str) -> Any:
    return api.request("ivy", "GET", contract.MATCH.format(match_id=match_id)).json()


@pytest.mark.slow
def test_it_03_10_the_worker_probes_a_clip_as_its_own_role(
    api: ApiDriver, committed_db: Any, worker_env: None
) -> None:
    match_id = _send(api, media.valid_clip_bytes(), "IT-03-10 probe")
    assert contract.WORKER_RUN_UNTIL_IDLE.load()() >= 1
    assert media_facts_count(committed_db, match_id) == 1
    assert _status(api, match_id)["media"] is not None


@pytest.mark.slow
def test_it_03_10_the_worker_refuses_a_long_clip_as_its_own_role(
    api: ApiDriver, committed_db: Any, worker_env: None
) -> None:
    match_id = _send(api, media.long_clip_bytes(), "IT-03-10 refuse")
    contract.WORKER_RUN_UNTIL_IDLE.load()()
    body = _status(api, match_id)
    assert body["rejection"]["code"] == "too_long"
    assert (body["upload"], body["media"]) == (None, None)


@pytest.mark.slow
def test_it_03_10_a_malformed_file_ends_failed_as_its_own_role(
    api: ApiDriver, committed_db: Any, worker_env: None
) -> None:
    head = media.valid_clip_bytes()[:32]
    data = head + bytes((i * 131 + 7) % 256 for i in range(64 * 1024))
    match_id = _send(api, data, "IT-03-10 malformed")
    contract.WORKER_RUN_UNTIL_IDLE.load()()
    assert _status(api, match_id)["status"] == "probe_failed"
