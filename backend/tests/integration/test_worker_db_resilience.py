"""R1-06 regression: a database error in the poll loop must not kill the worker.

Boundary crossed: a real ``python -m racket.worker`` process against real Postgres 16. The
worker's connection uses a ``search_path`` that points at an empty schema, so every claim
fails with ``UndefinedTable`` -- the same error as a worker that starts before the API has
migrated the database (QA-R1-02). The worker must log it, back off, keep polling and keep its
heartbeat fresh, and still stop cleanly on SIGTERM (NFR-046b).
"""

from __future__ import annotations

import json
import signal
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from sqlalchemy import text

from tests.support.db import database_url
from tests.support.worker import worker_process


@pytest.fixture
def empty_schema_url(raw_db_engine: Any) -> Iterator[str]:
    schema = f"r1_empty_{uuid.uuid4().hex[:8]}"
    with raw_db_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = database_url()
    sep = "&" if "?" in url else "?"
    yield f"{url}{sep}options={quote(f'-csearch_path={schema}')}"
    with raw_db_engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


def test_the_worker_survives_database_errors_and_still_stops_cleanly(
    empty_schema_url: str, tmp_path: Path
) -> None:
    heartbeat = tmp_path / "heartbeat"
    with worker_process(
        DATABASE_URL=empty_schema_url,
        WORKER_POLL_MS="100",
        WORKER_HEARTBEAT_FILE=str(heartbeat),
    ) as proc:
        time.sleep(4)
        alive = proc.poll() is None
        fresh = heartbeat.exists() and time.time() - heartbeat.stat().st_mtime < 3
        proc.send_signal(signal.SIGTERM)
        rc = proc.wait(timeout=10)
        assert proc.stdout is not None
        output = proc.stdout.read().decode(errors="replace")

    assert alive, output[-2000:]
    assert fresh, "heartbeat not refreshed while the database was failing"
    assert rc == 0, output[-2000:]
    events = [json.loads(line).get("event") for line in output.splitlines() if line.startswith("{")]
    assert events.count("worker.db_error") >= 2, events  # it kept polling after the first error
    assert "worker.stop" in events
