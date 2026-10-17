"""IT-04-13 (ST-059; FR-141; QD-DR-05; drill-review-checklist §3): CLI <-> files, the drill
coverage matrix check.

* rc 1 on ``backend/tests/fixtures/drills-coverage-gap/``, naming the one empty cell
  (``AN-05 x beginner: players <= 2: 0``, printed with the signs of
  drill-review-checklist §3) and nothing else: its draft, deprecated and superseded
  AN-05 beginner pairs drills do not count.
* rc 1, independently of that fixture, on copies of ``content/drills``: with every
  ``share:forced-error`` drill removed (the three AN-07:forced-error cells are named), with one
  file that is not valid JSON, and with fewer than 20 reviewed drills.
* rc 2 on a path that does not exist.
* rc 0 on ``content/drills``: it prints the 18-row matrix (target, level, drills,
  ``players ≤ 2``, no ball machine) and the library count.
* ``racket-drill-coverage`` is a console script of the backend package, and the ``drill-lint`` CI
  job runs it on ``../content/drills``.

The CLI is ``racket.coaching.drills.coverage:main`` (sprint-04 §3.7 ST-059 dirs). Every test that
changes a library works on a copy under ``tmp_path``; the repository is never written. Written
red first (ST-059 test commit).
"""

from __future__ import annotations

import json
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
LEVELS = ("beginner", "intermediate", "advanced")
_ROW = re.compile(r"^AN-\d{2}(:[a-z-]+)?\s+(beginner|intermediate|advanced)\s+\d+\s+\d+\s+\d+$")


def MATRIX_ROWS(out: str) -> int:
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


def _docs(folder: Path) -> list[tuple[Path, dict[str, object]]]:
    return [(p, json.loads(p.read_text())) for p in sorted(folder.glob("*/v*.json"))]


# ---------------------------------------------------------------- negative cases first
def test_it_04_13_the_gap_fixture_fails_naming_only_the_empty_cell(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc, out = run(capsys, GAP)
    assert rc == 1, out
    assert fails(out) == [f"FAIL {GAP_CELL}"], out
    assert MATRIX_ROWS(out) == 18, out


def test_it_04_13_a_library_without_forced_error_drills_names_its_three_cells(
    library: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    removed = [p for p, d in _docs(library) if "share:forced-error" in d["skills"]]  # type: ignore[operator]
    assert removed, "content/drills has no share:forced-error drill"
    for path in removed:
        path.unlink()
    rc, out = run(capsys, library)
    assert rc == 1, out
    for level in LEVELS:
        assert f"FAIL AN-07:forced-error × {level}: drills: 0" in fails(out), out


def test_it_04_13_a_file_that_is_not_json_fails_naming_the_file(
    library: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (library / "pb.broken").mkdir()
    (library / "pb.broken" / "v1.json").write_text("{not json")
    rc, out = run(capsys, library)
    assert rc == 1, out
    assert any("pb.broken/v1.json" in line and "invalid drill" in line for line in fails(out)), out


def test_it_04_13_fewer_than_20_reviewed_drills_fails(
    library: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for path, doc in _docs(library)[:8]:
        path.write_text(json.dumps({**doc, "review_status": "draft"}, indent=2) + "\n")
    rc, out = run(capsys, library)
    assert rc == 1, out
    assert any(re.fullmatch(r"FAIL library: \d+ < 20 reviewed drills", f) for f in fails(out)), out


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
    assert MATRIX_ROWS(out) == 18, out
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
