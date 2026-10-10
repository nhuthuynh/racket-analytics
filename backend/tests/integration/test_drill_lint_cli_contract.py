"""The ``racket-drill-lint`` CLI contract against real files (ST-053 review round 1:
PE-R1-ST053-01, PE-R1-ST053-02, SBE-R1-01; FR-140; QD-DR-02).

* rc 2: a path that does not exist; a lock (the library's or the base branch's) that cannot be
  read or is not a ``drill-library-lock/v1`` file.
* rc 1: a drill file that is not JSON ("invalid json"); a library with no ``library.lock``
  ("no lock").
* ``--update-lock`` writes the new version to ``library.lock`` and nothing else, and refuses to
  write while any other problem exists (the file keeps its bytes).
* ``--base-lock`` (or ``RACKET_DRILL_BASE_LOCK``, which CI fills from the base branch): a
  deletion or an in-place edit fails even when the same change rewrites ``library.lock``.

Each test works on a copy of ``content/drills`` under ``tmp_path``; the repository is never
written.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.integration.test_it_03_14_drill_lint import LIBRARY, LINT

LOCK = "library.lock"
DROP_LADDER = "pb.fixture.drop-ladder"
ENV = "RACKET_DRILL_BASE_LOCK"


@pytest.fixture
def library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv(ENV, raising=False)
    copy = tmp_path / "drills"
    shutil.copytree(LIBRARY, copy)
    return copy


@pytest.fixture
def base_lock(tmp_path: Path) -> Path:
    """The base branch's lock: here the library's lock before the PR's change."""
    path = tmp_path / "base.lock"
    shutil.copyfile(LIBRARY / LOCK, path)
    return path


def run(capsys: pytest.CaptureFixture[str], *argv: object) -> tuple[int, str]:
    capsys.readouterr()
    rc = LINT.load()([str(a) for a in argv])
    out, err = capsys.readouterr()
    return int(rc), out + err


def drop_lock_line(library: Path, version: str) -> None:
    lock = json.loads((library / LOCK).read_text())
    del lock["drills"][version]
    (library / LOCK).write_text(json.dumps(lock, indent=2) + "\n")


def edit_v3(library: Path) -> None:
    path = library / DROP_LADDER / "v3.json"
    doc = json.loads(path.read_text())
    doc["summary"] = doc["summary"] + " Edited in place."
    path.write_text(json.dumps(doc, indent=2) + "\n")


# ---------------------------------------------------------------- negative cases first
def test_a_path_that_does_not_exist_is_rc_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc, out = run(capsys, tmp_path / "nowhere")
    assert rc == 2, out
    assert "no such file or directory" in out


@pytest.mark.parametrize("text", ["{not json", '{"schema": "something-else/v1", "drills": {}}'])
def test_an_unreadable_or_foreign_library_lock_is_rc_2(
    library: Path, capsys: pytest.CaptureFixture[str], text: str
) -> None:
    (library / LOCK).write_text(text)
    rc, out = run(capsys, library)
    assert rc == 2, out
    assert "unreadable lock" in out


@pytest.mark.parametrize("text", [None, "{not json", '{"schema": "x/v1", "drills": {}}'])
def test_a_missing_unreadable_or_foreign_base_lock_is_rc_2(
    library: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str | None
) -> None:
    base = tmp_path / "base.lock"
    if text is not None:
        base.write_text(text)
    rc, out = run(capsys, library, "--base-lock", base)
    assert rc == 2, out
    assert "base.lock" in out


def test_a_drill_file_that_is_not_json_is_rc_1(
    library: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (library / DROP_LADDER / "v4.json").write_text('{"id": "pb.fixture.drop-ladder",')
    rc, out = run(capsys, library)
    assert rc == 1, out
    assert f"FAIL {DROP_LADDER}/v4.json: drill ?: invalid json:" in out


def test_a_library_without_a_lock_is_rc_1(
    library: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (library / LOCK).unlink()
    rc, out = run(capsys, library)
    assert rc == 1, out
    assert f"FAIL {LOCK}: drill ?: no lock:" in out


def test_update_lock_refuses_to_write_while_an_edit_exists(
    library: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    edit_v3(library)
    new = json.loads((library / "pb.fixture.serve-target" / "v1.json").read_text())
    new["id"] = "pb.fixture.serve-target-deep"
    (library / "pb.fixture.serve-target" / "deep.json").write_text(json.dumps(new))
    before = (library / LOCK).read_bytes()
    rc, out = run(capsys, library, "--update-lock")
    assert rc == 1, out
    assert "edited without version bump" in out
    assert "not in lock" in out
    assert (library / LOCK).read_bytes() == before


def test_deleting_a_drill_and_its_lock_line_fails_against_the_base_lock(
    library: Path, base_lock: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (library / DROP_LADDER / "v1.json").unlink()
    drop_lock_line(library, f"{DROP_LADDER}@1")
    assert run(capsys, library)[0] == 0  # without the base lock this passed (the finding)
    rc, out = run(capsys, library, "--base-lock", base_lock)
    assert rc == 1, out
    assert "deleted drill" in out
    assert "lock entry removed" in out
    assert DROP_LADDER in out


def test_an_in_place_edit_relocked_with_update_lock_fails_against_the_base_lock(
    library: Path, base_lock: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    edit_v3(library)
    drop_lock_line(library, f"{DROP_LADDER}@3")
    assert run(capsys, library, "--update-lock")[0] == 0  # the finding's bypass, no base lock
    rc, out = run(capsys, library, "--base-lock", base_lock)
    assert rc == 1, out
    assert "edited without version bump" in out
    assert "lock entry changed" in out


def test_a_deleted_lock_is_not_rebuilt_past_the_base_lock(
    library: Path, base_lock: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (library / DROP_LADDER / "v1.json").unlink()
    (library / LOCK).unlink()
    rc, out = run(capsys, library, "--update-lock", "--base-lock", base_lock)
    assert rc == 1, out
    assert "lock entry removed" in out
    assert "deleted drill" in out
    assert not (library / LOCK).exists()


def test_the_base_lock_comes_from_the_environment_when_no_flag_is_given(
    library: Path,
    base_lock: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (library / DROP_LADDER / "v1.json").unlink()
    drop_lock_line(library, f"{DROP_LADDER}@1")
    monkeypatch.setenv(ENV, str(base_lock))
    rc, out = run(capsys, library)
    assert rc == 1, out
    assert "lock entry removed" in out


# ---------------------------------------------------------------- positive cases
def test_update_lock_writes_only_the_new_version(
    library: Path, base_lock: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    v3 = json.loads((library / DROP_LADDER / "v3.json").read_text())
    (library / DROP_LADDER / "v4.json").write_text(json.dumps({**v3, "version": 4}))
    rc, out = run(capsys, library, "--base-lock", base_lock)
    assert rc == 1, out
    assert "not in lock" in out, out
    before = json.loads((library / LOCK).read_text())["drills"]
    rc, out = run(capsys, library, "--update-lock", "--base-lock", base_lock)
    assert rc == 0, out
    after = json.loads((library / LOCK).read_text())
    assert after["schema"] == "drill-library-lock/v1"
    assert set(after["drills"]) - set(before) == {f"{DROP_LADDER}@4"}
    assert {k: after["drills"][k] for k in before} == before
    assert list(after["drills"]) == sorted(after["drills"])
    assert run(capsys, library, "--base-lock", base_lock) == (0, out.splitlines()[-1] + "\n")


def test_the_unchanged_library_passes_against_its_base_lock(
    library: Path, base_lock: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc, out = run(capsys, library, "--base-lock", base_lock)
    assert rc == 0, out
    assert "ok, 0 problem(s)" in out


def test_an_empty_base_lock_is_a_base_branch_without_drills(
    library: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty = tmp_path / "empty.lock"
    empty.write_text('{"schema": "drill-library-lock/v1", "drills": {}}\n')
    rc, out = run(capsys, library, "--base-lock", empty)
    assert rc == 0, out
