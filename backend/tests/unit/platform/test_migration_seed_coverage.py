"""ST-082 unit tests (REL-1.3; PE F3 on PR #224): the IT-05-10 seed has a row in every table
whose columns, indexes or constraints a ``downgrade()`` changes while the table outlives it, so a
data-dependent downgrade (like 0005's before its fix) fails the round trip instead of passing on
an empty table. Planted modules in a temp directory for the parser; no database."""

from __future__ import annotations

from pathlib import Path

import pytest

from racket.platform.db import MIGRATIONS_DIR
from tests.support.migration_roundtrip import SEED, data_dependent_tables, seeded_tables

pytestmark = pytest.mark.unit


def _plant(tmp_path: Path, name: str, downgrade: str) -> None:
    (tmp_path / f"{name}.py").write_text(
        f'"""m"""\nrevision = "{name}"\n\n\ndef upgrade() -> None:\n    op.f()\n\n\n'
        f"def downgrade() -> None:\n{downgrade}\n"
    )


def test_column_index_and_constraint_changes_name_their_table(tmp_path: Path) -> None:
    _plant(tmp_path, "0001", '    op.drop_column("a", "x")\n    op.add_column("b", col)')
    _plant(tmp_path, "0002", '    op.drop_constraint("c_k", "c", type_="unique")')
    _plant(tmp_path, "0003", '    op.create_unique_constraint("uq", "d", ["k"])')
    _plant(tmp_path, "0004", '    op.drop_index("ix", "e")\n    op.alter_column("f", "y")')
    assert data_dependent_tables(tmp_path) == {"a", "b", "c", "d", "e", "f"}


def test_a_table_the_same_downgrade_drops_is_not_named(tmp_path: Path) -> None:
    _plant(tmp_path, "0001", '    op.drop_index("ix", "g")\n    op.drop_table("g")')
    assert data_dependent_tables(tmp_path) == set()


def test_seeded_tables_reads_the_insert_targets() -> None:
    seeded = seeded_tables(("INSERT INTO t1 (a) VALUES (1)", "insert into  t2 (b) values (2)"))
    assert seeded == {"t1", "t2"}


def test_the_seed_covers_every_table_a_downgrade_changes() -> None:
    missing = data_dependent_tables(MIGRATIONS_DIR / "versions") - seeded_tables(SEED)
    assert missing == set(), f"seed a row in {sorted(missing)} (IT-05-10)"
