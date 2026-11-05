"""ST-082 unit tests (REL-1.3 negative; ADR 0058 rule 7): ``missing_downgrades`` names every
migration module whose ``downgrade()`` is absent or does nothing. Planted modules in a temp
directory; no database."""

from __future__ import annotations

from pathlib import Path

import pytest

from racket.platform.db import MIGRATIONS_DIR
from tests.support.migration_roundtrip import missing_downgrades

pytestmark = pytest.mark.unit

HEAD = '"""m"""\nrevision = "{rev}"\ndown_revision = {down}\n\n\ndef upgrade() -> None:\n    op.f()\n\n'


def _plant(tmp_path: Path, rev: str, down: str, downgrade: str | None) -> None:
    body = HEAD.format(rev=rev, down=down)
    if downgrade is not None:
        body += f"\ndef downgrade() -> None:\n{downgrade}\n"
    (tmp_path / f"{rev}_m.py").write_text(body)


def test_a_migration_without_a_downgrade_is_named(tmp_path: Path) -> None:
    _plant(tmp_path, "0001", "None", "    op.g()")
    _plant(tmp_path, "0002", '"0001"', None)
    assert missing_downgrades(tmp_path) == ["0002"]


@pytest.mark.parametrize(
    "body",
    ["    pass", '    """Irreversible."""', "    ...", '    raise NotImplementedError("one way")'],
)
def test_a_downgrade_that_does_nothing_is_named(tmp_path: Path, body: str) -> None:
    _plant(tmp_path, "0003", '"0002"', body)
    assert missing_downgrades(tmp_path) == ["0003"]


def test_a_downgrade_with_a_docstring_and_a_statement_counts(tmp_path: Path) -> None:
    _plant(tmp_path, "0004", '"0003"', '    """Drop it."""\n    op.drop_table("t")')
    assert missing_downgrades(tmp_path) == []


def test_the_revision_id_comes_from_the_module_not_the_file_name(tmp_path: Path) -> None:
    (tmp_path / "abc_named.py").write_text(HEAD.format(rev="0042", down="None"))
    assert missing_downgrades(tmp_path) == ["0042"]


def test_every_real_migration_has_a_downgrade() -> None:
    assert missing_downgrades(MIGRATIONS_DIR / "versions") == []
