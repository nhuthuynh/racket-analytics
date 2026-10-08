"""ST-042 (NFR-054; SEC-R1S3-01): migrations 0012 and 0013 grant the media sandbox worker role
only the probe stage's privileges. No I/O: ``op`` is a recorder, the SQL is read as text.
Real-database proof is IT-03-10 / IT-03-10b and tests/features/media_worker_identity.feature.
"""

from __future__ import annotations

import importlib
import re
from types import ModuleType

import pytest

pytestmark = pytest.mark.unit

ROLE = "racket_media_worker"
IDENTITY_TABLES = {"accounts", "sessions", "sign_in_links", "sign_in_requests"}
PROBE_TABLES = {
    "jobs",
    "media_assets",
    "media_facts",
    "upload_sessions",
    "matches",
    "match_participants",
}
_GRANT_TABLE = re.compile(r"^GRANT (.+) ON TABLE (\w+) TO (\w+)$")
_GRANT_COLUMNS = re.compile(r"^GRANT UPDATE \(([^)]*)\) ON TABLE (\w+) TO (\w+)$")


class _Op:
    def __init__(self) -> None:
        self.sql: list[str] = []

    def execute(self, statement: str) -> None:
        self.sql.append(" ".join(str(statement).split()))


def _run(name: str, step: str, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    module: ModuleType = importlib.import_module(f"racket.migrations.versions.{name}")
    recorder = _Op()
    monkeypatch.setattr(module, "op", recorder)
    getattr(module, step)()
    return recorder.sql


def _module(name: str) -> ModuleType:
    return importlib.import_module(f"racket.migrations.versions.{name}")


# ------------------------------------------------------------------ negative cases first
def test_0012_grants_nothing_on_identity_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    sql = _run("0012_media_worker_role", "upgrade", monkeypatch)
    touched = {m.group(2) for s in sql if (m := _GRANT_TABLE.match(s))}
    assert touched.isdisjoint(IDENTITY_TABLES)
    assert touched <= PROBE_TABLES


def test_0012_tolerates_a_concurrent_migrator_creating_the_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Roles are cluster-wide, the migration lock is per database: a loser of the NOT EXISTS
    # race gets unique_violation (or duplicate_object) and must treat it as "already there".
    [create] = [
        s for s in _run("0012_media_worker_role", "upgrade", monkeypatch) if "CREATE ROLE" in s
    ]
    assert "EXCEPTION WHEN duplicate_object OR unique_violation THEN" in create


def test_0012_creates_a_role_that_cannot_log_in(monkeypatch: pytest.MonkeyPatch) -> None:
    sql = " ".join(_run("0012_media_worker_role", "upgrade", monkeypatch))
    assert f"CREATE ROLE {ROLE} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE" in sql
    assert "PASSWORD" not in sql.upper()


def test_0012_never_grants_all_or_default_privileges(monkeypatch: pytest.MonkeyPatch) -> None:
    sql = _run("0012_media_worker_role", "upgrade", monkeypatch)
    assert not [s for s in sql if "GRANT ALL" in s or "DEFAULT PRIVILEGES" in s]
    assert not [s for s in sql if "INSERT" in s and "jobs" in s]  # enqueue is the API's


def test_0013_takes_back_table_wide_update_on_matches_and_media(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sql = _run("0013_media_worker_column_grants", "upgrade", monkeypatch)
    assert f"REVOKE UPDATE ON TABLE matches FROM {ROLE}" in sql
    assert f"REVOKE UPDATE ON TABLE media_assets FROM {ROLE}" in sql


@pytest.mark.parametrize(
    ("table", "column"),
    [("matches", "owner_id"), ("matches", "title"), ("matches", "rules_version"),
     ("matches", "version"), ("media_assets", "owner_id"), ("media_assets", "object_key"),
     ("media_assets", "match_id")],
)  # fmt: skip
def test_0013_never_lets_the_worker_update_ownership_or_key_columns(
    monkeypatch: pytest.MonkeyPatch, table: str, column: str
) -> None:
    sql = _run("0013_media_worker_column_grants", "upgrade", monkeypatch)
    granted = {
        (m.group(2), c.strip()) for s in sql if (m := _GRANT_COLUMNS.match(s))
        for c in m.group(1).split(",")
    }  # fmt: skip
    assert (table, column) not in granted


# ------------------------------------------------------------------ positive controls
def test_0012_grants_the_probe_stage_its_reads_and_job_updates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sql = _run("0012_media_worker_role", "upgrade", monkeypatch)
    assert f"GRANT USAGE ON SCHEMA public TO {ROLE}" in sql
    grants = {m.group(2): m.group(1) for s in sql if (m := _GRANT_TABLE.match(s))}
    assert set(grants) == PROBE_TABLES
    assert grants["jobs"] == "SELECT, UPDATE"


def test_0013_grants_update_on_the_probe_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    sql = _run("0013_media_worker_column_grants", "upgrade", monkeypatch)
    assert f"GRANT UPDATE (probe_status, updated_at) ON TABLE media_assets TO {ROLE}" in sql
    assert (
        "GRANT UPDATE (status, media_asset_id, rejection_code, rejected_at, updated_at) "
        f"ON TABLE matches TO {ROLE}"
    ) in sql


def test_the_migrations_chain_0011_0012_0013() -> None:
    assert (
        _module("0012_media_worker_role").down_revision,
        _module("0012_media_worker_role").revision,
    ) == ("0011", "0012")
    assert _module("0013_media_worker_column_grants").down_revision == "0012"


def test_downgrades_undo_the_grants(monkeypatch: pytest.MonkeyPatch) -> None:
    down12 = _run("0012_media_worker_role", "downgrade", monkeypatch)
    assert {f"REVOKE ALL ON TABLE {t} FROM {ROLE}" for t in PROBE_TABLES} <= set(down12)
    assert any("DROP ROLE IF EXISTS racket_media_worker" in s for s in down12)
    down13 = _run("0013_media_worker_column_grants", "downgrade", monkeypatch)
    assert f"GRANT UPDATE ON TABLE matches TO {ROLE}" in down13
