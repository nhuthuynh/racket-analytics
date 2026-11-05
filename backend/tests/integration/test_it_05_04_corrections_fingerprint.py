"""IT-05-04 (ST-076b; NFR-045.3; ADR 0058 rule 4 step 10): the confirmed-corrections
fingerprint (count + SHA-256) is equal after ``pg_dump``/``pg_restore`` and differs after a
planted deleted row; ``racket-integrity`` exits 1 on that mismatch, naming "corrections".

Real Postgres (AQS/OPS-05). Negative first: the planted deleted row.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from racket.platform import integrity as cli
from tests.support import integrity as it
from tests.support.api import ApiDriver


@pytest.fixture
def audited(api: ApiDriver, committed_db: Any) -> str:
    return it.audited_match(api)


def test_it_05_04_a_planted_deleted_correction_changes_the_fingerprint(
    committed_db: Any, audited: str
) -> None:
    count, digest = it.fingerprint(committed_db)
    assert count == it.correction_count(committed_db) >= 3  # game start, correction, undo
    it.plant_deleted_correction(committed_db, audited)
    after_count, after_digest = it.fingerprint(committed_db)
    assert after_count == count - 1
    assert after_digest != digest


def test_it_05_04_fingerprint_is_equal_after_dump_and_restore(
    committed_db: Any, audited: str
) -> None:
    before = it.fingerprint(committed_db)
    with it.restored_copy(committed_db) as restored:
        assert it.fingerprint(restored) == before


def test_it_05_04_restore_of_a_dump_with_a_lost_row_is_detected(
    committed_db: Any, audited: str
) -> None:
    before = it.fingerprint(committed_db)
    it.plant_deleted_correction(committed_db, audited)
    with it.restored_copy(committed_db) as restored:
        assert it.fingerprint(restored) != before


def test_it_05_04_empty_table_fingerprint_is_zero_and_the_empty_digest(committed_db: Any) -> None:
    assert it.fingerprint(committed_db) == (
        0,
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )


def test_it_05_04_cli_prints_the_fingerprint_and_exits_0_when_it_matches(
    committed_db: Any, audited: str, monkeypatch: pytest.MonkeyPatch, capsys: Any
) -> None:
    monkeypatch.setenv("DATABASE_URL", it.libpq_url(committed_db))
    count, digest = it.fingerprint(committed_db)
    assert cli.main([]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "corrections": {"count": count, "sha256": digest}
    }
    rc = cli.main(["--expect-count", str(count), "--expect-sha256", digest])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["corrections"]["equal"] is True


def test_it_05_04_cli_exits_1_naming_corrections_after_a_planted_delete(
    committed_db: Any, audited: str, monkeypatch: pytest.MonkeyPatch, capsys: Any
) -> None:
    monkeypatch.setenv("DATABASE_URL", it.libpq_url(committed_db))
    count, digest = it.fingerprint(committed_db)
    it.plant_deleted_correction(committed_db, audited)
    rc = cli.main(["--expect-count", str(count), "--expect-sha256", digest])
    captured = capsys.readouterr()
    assert rc == 1
    assert json.loads(captured.out)["corrections"]["equal"] is False
    assert "corrections" in captured.err
