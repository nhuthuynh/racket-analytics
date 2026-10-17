"""IT-04-13 (ST-059; FR-141; QD-DR-05): CLI <-> files, ``racket-drill-coverage``.

rc 1 on ``backend/tests/fixtures/drills-coverage-gap/`` naming its one empty cell and nothing else
(its draft, deprecated and superseded AN-05 beginner pairs drills do not count); rc 1 naming a
file that is not JSON (on a ``tmp_path`` copy of ``content/drills``); rc 2 on a missing path;
rc 0 on ``content/drills`` with the 18-row matrix and the library count. The console script is
registered and the ``drill-lint`` CI job runs it. The cell and library rules are unit-tested in
``tests/unit/coaching/test_coverage.py``. Written red first (ST-059 test commit).
"""

from __future__ import annotations

import re
import shutil
from importlib.metadata import entry_points
from pathlib import Path

import pytest

from tests.support.contract import Seam
from tests.support.paths import REPO

COVERAGE = Seam("racket.coaching.drills.coverage:main", "ST-059", "main(argv: list[str]) -> int")
LIBRARY = REPO / "content" / "drills"
GAP = REPO / "backend" / "tests" / "fixtures" / "drills-coverage-gap"
GAP_CELL = "AN-05 × beginner: players ≤ 2: 0"
_ROW = re.compile(r"^AN-\d{2}(:[a-z-]+)?\s+(beginner|intermediate|advanced)\s+\d+\s+\d+\s+\d+$")


def matrix_rows(out: str) -> int:
    return sum(bool(_ROW.match(line)) for line in out.splitlines())


def run(capsys: pytest.CaptureFixture[str], *argv: object) -> tuple[int, str]:
    capsys.readouterr()
    rc = COVERAGE.load()([str(a) for a in argv])
    out, err = capsys.readouterr()
    return int(rc), out + err


def fails(out: str) -> list[str]:
    return [line for line in out.splitlines() if line.startswith("FAIL ")]


@pytest.fixture
def library(tmp_path: Path) -> Path:
    copy = tmp_path / "drills"
    shutil.copytree(LIBRARY, copy)
    return copy


# ---------------------------------------------------------------- negative cases first
def test_it_04_13_the_gap_fixture_fails_naming_only_the_empty_cell(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc, out = run(capsys, GAP)
    assert rc == 1, out
    assert fails(out) == [f"FAIL {GAP_CELL}"], out
    assert matrix_rows(out) == 18, out


def test_it_04_13_a_file_that_is_not_json_fails_naming_the_file(
    library: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (library / "pb.broken").mkdir()
    (library / "pb.broken" / "v1.json").write_text("{not json")
    rc, out = run(capsys, library)
    assert rc == 1, out
    assert any("pb.broken/v1.json" in line and "invalid drill" in line for line in fails(out)), out


def test_it_04_13_a_path_that_does_not_exist_is_rc_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc, out = run(capsys, tmp_path / "nowhere")
    assert rc == 2, out
    assert "no such directory" in out


# ---------------------------------------------------------------- the starter library passes
def test_it_04_13_the_starter_library_passes_and_prints_the_matrix(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc, out = run(capsys, LIBRARY)
    assert rc == 0, out
    assert fails(out) == [], out
    assert matrix_rows(out) == 18, out
    found = re.search(r"library: (\d+) reviewed drill\(s\), (\d+) warm-up\(s\)", out)
    assert found, out
    assert int(found.group(1)) >= 20, out
    assert int(found.group(2)) >= 3, out


def test_it_04_13_the_console_script_and_the_ci_job() -> None:
    scripts = entry_points(group="console_scripts", name="racket-drill-coverage")
    assert [s.value for s in scripts] == ["racket.coaching.drills.coverage:main"]
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text()
    job = re.search(r"^  drill-lint:\n(.*?)(?=^  [a-z][\w-]*:\n)", ci, re.M | re.S)
    assert job, "no drill-lint job in ci.yml"
    assert re.search(
        r"^\s+- run: uv run --no-sync racket-drill-coverage ../content/drills$", job.group(1), re.M
    ), job.group(1)
