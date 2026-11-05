"""Binding of tests/features/corrections_fingerprint.feature (ST-076b; NFR-045.3; ADR 0058
rule 4 step 10). Real Postgres, real ``pg_dump``/``pg_restore``; the CLI is called in process."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from racket.platform import integrity as cli
from tests.support import integrity as it
from tests.support.api import ApiDriver

FEATURE = "corrections_fingerprint.feature"


@scenario(FEATURE, "A dump restored into an empty database keeps every confirmed correction")
def test_a_dump_restored_into_an_empty_database_keeps_every_confirmed_correction() -> None:
    pass


@scenario(FEATURE, "A deleted correction is detected")
def test_a_deleted_correction_is_detected() -> None:
    pass


@scenario(FEATURE, "A backup that holds a deleted match stays equal after restore and purge")
def test_a_backup_that_holds_a_deleted_match_stays_equal_after_restore_and_purge() -> None:
    pass


@pytest.fixture
def ctx(api: ApiDriver, committed_db: Any) -> dict[str, Any]:
    return {"api": api, "db": committed_db}


@given("Ivy's match has a confirmed correction and its undo")
def audited(ctx: dict[str, Any]) -> None:
    ctx["match"] = it.audited_match(ctx["api"])


@given("the corrections fingerprint is recorded")
def recorded(ctx: dict[str, Any]) -> None:
    ctx["before"] = it.fingerprint(ctx["db"])
    assert ctx["before"][0] >= 3


@when("the database is dumped and restored into an empty database")
def dump_and_restore(ctx: dict[str, Any]) -> None:
    with it.restored_copy(ctx["db"]) as restored:
        ctx["restored"] = it.fingerprint(restored)


@then("the restored database has the same corrections count and SHA-256")
def same_after_restore(ctx: dict[str, Any]) -> None:
    assert ctx["restored"] == ctx["before"]


@given("Ivy's second match with corrections is deleted but not yet purged")
def deleted_match(ctx: dict[str, Any]) -> None:
    ctx["gone"] = it.audited_match(ctx["api"], title="IT-05-04 gone")
    it.tombstone(ctx["api"], ctx["gone"])
    assert it.correction_count_of(ctx["db"], ctx["gone"]) >= 3


@when("the database is dumped and restored into an empty database and the purge runs on it")
def dump_restore_and_purge(ctx: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    with it.restored_copy(ctx["db"]) as restored:
        it.purge(restored, monkeypatch)
        ctx["gone_rows"] = it.correction_count_of(restored, ctx["gone"])
        ctx["restored"] = it.fingerprint(restored)


@then("the deleted match has no correction rows in the restored database")
def gone_after_purge(ctx: dict[str, Any]) -> None:
    assert ctx["gone_rows"] == 0


@when("one confirmed correction row is deleted behind the append-only guard")
def planted_delete(ctx: dict[str, Any]) -> None:
    it.plant_deleted_correction(ctx["db"], ctx["match"])


@then("the corrections count is one lower and the SHA-256 differs")
def one_lower(ctx: dict[str, Any]) -> None:
    count, digest = it.fingerprint(ctx["db"])
    assert count == ctx["before"][0] - 1
    assert digest != ctx["before"][1]


@then(parsers.parse('racket-integrity checked against the recorded values exits 1 naming "{name}"'))
def cli_fails(ctx: dict[str, Any], name: str, monkeypatch: pytest.MonkeyPatch, capsys: Any) -> None:
    monkeypatch.setenv("DATABASE_URL", it.libpq_url(ctx["db"]))
    count, digest = ctx["before"]
    rc = cli.main(["--expect-count", str(count), "--expect-sha256", digest])
    captured = capsys.readouterr()
    assert rc == 1
    assert json.loads(captured.out)[name]["equal"] is False
    assert name in captured.err
