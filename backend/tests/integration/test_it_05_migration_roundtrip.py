"""IT-05-10 (ST-082; REL-1.3; ADR 0058 rule 7): every Alembic migration since the R1 baseline
(0001: R1 is the first release) steps down one revision and up again on a seeded scratch
database, with the same schema and no lost seed row in a table that outlived the downgrade.

The scratch database sits beside the session's own (``tests.support.db``) and is dropped
afterwards, so the downgrades never touch the database other tests use. The negative case (a
migration without ``downgrade``) is the unit test ``test_migration_downgrades_present.py`` and
the scenario in ``tests/features/migration_roundtrip.feature``.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from racket.platform.db import MIGRATIONS_DIR
from tests.support.db import BASE_URL_ENV, database_url
from tests.support.migration_roundtrip import (
    migrate,
    missing_downgrades,
    revisions,
    round_trip,
    scratch_database,
    seed,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def seeded_url() -> Iterator[str]:
    base = os.environ.get(BASE_URL_ENV) or database_url()
    with scratch_database(base) as url:
        migrate(url, "head")
        seed(url)
        yield url


def test_it_05_10_every_migration_round_trips_on_a_seeded_copy(seeded_url: str) -> None:
    assert missing_downgrades(MIGRATIONS_DIR / "versions") == []
    steps = round_trip(seeded_url)
    assert [s.revision for s in steps] == [r for r, _ in revisions()]
    assert len(steps) >= 21  # 0001-0021 at the R1 release candidate
    for step in steps:
        assert step.back_at == step.revision, step
        assert step.schema_equal, f"{step.revision}: schema differs after down and up"
        assert step.lost_rows == {}, f"{step.revision}: rows lost {step.lost_rows}"
