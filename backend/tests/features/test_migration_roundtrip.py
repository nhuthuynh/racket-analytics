"""Binds tests/features/migration_roundtrip.feature (ST-082; REL-1.3; ADR 0058 rule 7). The
happy scenario runs on a seeded scratch database beside the session's own; the negative one on
planted migration modules."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from racket.platform.db import MIGRATIONS_DIR
from tests.support.db import BASE_URL_ENV, database_url
from tests.support.migration_roundtrip import (
    SEED,
    data_dependent_tables,
    migrate,
    missing_downgrades,
    round_trip,
    scratch_database,
    seed,
    seeded_tables,
)

scenarios("migration_roundtrip.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@pytest.fixture
def scratch() -> Any:
    base = os.environ.get(BASE_URL_ENV) or database_url()
    with scratch_database(base) as url:
        yield url


@given("a scratch database at the head revision with seed rows")
def seeded(ctx: dict[str, Any], scratch: str) -> None:
    migrate(scratch, "head")
    seed(scratch)
    ctx["url"] = scratch


@when("every migration is stepped down one revision and up again from the head")
def walk(ctx: dict[str, Any]) -> None:
    ctx["steps"] = round_trip(ctx["url"])


@then("every step returned to its revision with the same schema")
def same_schema(ctx: dict[str, Any]) -> None:
    assert ctx["steps"]
    assert all(s.back_at == s.revision and s.schema_equal for s in ctx["steps"]), ctx["steps"]


@then("no seed row in a table that outlived the downgrade was lost")
def no_loss(ctx: dict[str, Any]) -> None:
    assert [s for s in ctx["steps"] if s.lost_rows] == []


@given(parsers.parse('a migration directory where "{rev}" has no downgrade'))
def planted(ctx: dict[str, Any], tmp_path: Path, rev: str) -> None:
    (tmp_path / "0001_a.py").write_text(
        'revision = "0001"\ndown_revision = None\n\n\ndef upgrade():\n    op.f()\n\n\n'
        "def downgrade():\n    op.g()\n"
    )
    (tmp_path / f"{rev}_b.py").write_text(
        f'revision = "{rev}"\ndown_revision = "0001"\n\n\ndef upgrade():\n    op.f()\n'
    )
    ctx["dir"] = tmp_path


@when("the migrations are checked for a downgrade")
def check(ctx: dict[str, Any]) -> None:
    ctx["missing"] = missing_downgrades(ctx["dir"])


@then(parsers.parse('the check names "{rev}"'))
def named(ctx: dict[str, Any], rev: str) -> None:
    assert ctx["missing"] == [rev]


@given("the real migration directory")
def real_dir(ctx: dict[str, Any]) -> None:
    ctx["dir"] = MIGRATIONS_DIR / "versions"


@when("the tables whose columns or constraints a downgrade changes are listed")
def listed(ctx: dict[str, Any]) -> None:
    ctx["tables"] = data_dependent_tables(ctx["dir"])


@then("each of them has a seed row")
def each_seeded(ctx: dict[str, Any]) -> None:
    assert ctx["tables"], "no downgrade changes a table: the parser found nothing"
    assert ctx["tables"] - seeded_tables(SEED) == set()
