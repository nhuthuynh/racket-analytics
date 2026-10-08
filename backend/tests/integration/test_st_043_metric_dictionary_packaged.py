"""The metric dictionary ships inside the built backend package (ST-043; FR-102; NFR-075).

Integration (build + filesystem boundary): builds the real wheel with ``uv build`` and reads the
dictionary and its lock out of the archive, the way the API and worker images load them. A wheel
without ``metrics.json`` or with a stale ``metrics.lock.json`` would make the stats API fail
closed in production although every unit test passed against the source tree. No services needed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from racket.sports.pickleball.metrics import (
    LOCK_PATH,
    METRICS_PATH,
    DefinitionLock,
    MetricDictionary,
    definition_digest,
    load_dictionary,
    version_bump_violations,
)

pytestmark = pytest.mark.integration

BACKEND = Path(__file__).resolve().parents[2]
PACKAGE_DIR = "racket/sports/pickleball"


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> zipfile.ZipFile:
    uv = shutil.which("uv")
    assert uv is not None, "uv is required to build the backend wheel"
    out = tmp_path_factory.mktemp("wheel")
    subprocess.run(
        [uv, "build", "--wheel", "--out-dir", str(out)],
        cwd=BACKEND,
        check=True,
        capture_output=True,
        timeout=110,
    )
    (built,) = out.glob("*.whl")
    return zipfile.ZipFile(built)


def test_the_wheel_ships_the_dictionary_and_its_lock_unchanged(wheel: zipfile.ZipFile) -> None:
    names = set(wheel.namelist())
    for source in (METRICS_PATH, LOCK_PATH):
        member = f"{PACKAGE_DIR}/{source.name}"
        assert member in names, f"{member} missing from the wheel"
        assert wheel.read(member) == source.read_bytes(), f"{member} differs from the source"


def test_the_packaged_dictionary_loads_and_matches_its_lock(wheel: zipfile.ZipFile) -> None:
    dictionary = MetricDictionary.parse(json.loads(wheel.read(f"{PACKAGE_DIR}/metrics.json")))
    lock = json.loads(wheel.read(f"{PACKAGE_DIR}/metrics.lock.json"))
    assert [e.id for e in dictionary.entries] == [f"AN-0{i}" for i in range(1, 8)]
    assert lock["version"] == dictionary.version
    assert version_bump_violations(dictionary, DefinitionLock.parse(lock)) == ()
    reviewed = {e.id for e in dictionary.entries if e.status in ("coach-reviewed", "verified")}
    assert {e.id for e in dictionary.published()} == reviewed


# ---------------------------------------------------------------- NFR-075 against main (git)
# The lock is append-only. Compared with the lock at the merge base with main, a digest
# overwritten in place (a definition change with no version bump, PE-ST043-01) or a removed row
# is a violation. CI checks out with fetch-depth 0, so origin/main is present; the base ref can
# be overridden with METRICS_LOCK_BASE_REF.
def _git(*args: str) -> subprocess.CompletedProcess[str]:
    git = shutil.which("git")
    assert git is not None, "git is required to read the lock on main"
    return subprocess.run(
        [git, *args], cwd=BACKEND, capture_output=True, text=True, timeout=30, check=False
    )


def test_no_definition_changed_without_a_bump_since_main() -> None:
    base_ref = os.environ.get("METRICS_LOCK_BASE_REF", "origin/main")
    base = _git("merge-base", "HEAD", base_ref)
    assert base.returncode == 0, f"cannot find {base_ref} (fetch it; CI uses fetch-depth 0)"
    lock_path = LOCK_PATH.relative_to(BACKEND.parent).as_posix()
    on_main = _git("show", f"{base.stdout.strip()}:{lock_path}")
    previous = None
    if on_main.returncode == 0:
        previous = DefinitionLock.parse(json.loads(on_main.stdout))
    else:  # the lock does not exist on main yet (the PR that adds it)
        assert "does not exist" in on_main.stderr or "exists on disk" in on_main.stderr, (
            on_main.stderr
        )
    current = DefinitionLock.parse(json.loads(LOCK_PATH.read_text(encoding="utf-8")))
    assert version_bump_violations(load_dictionary(), current, previous=previous) == ()


def test_the_main_comparison_catches_a_digest_rewritten_in_place(tmp_path: Path) -> None:
    """The same git read, against a throwaway repo whose main has the shipped lock and whose
    branch changes AN-01's formula and overwrites its 0.1 digest without a bump."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env_git = ["-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    assert _git("init", "-q", "-b", "main", str(repo)).returncode == 0
    (repo / "metrics.lock.json").write_bytes(LOCK_PATH.read_bytes())
    assert _git(*env_git, "add", ".").returncode == 0
    assert _git(*env_git, "commit", "-q", "-m", "lock").returncode == 0
    data = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    data["entries"][0]["formula"] = "rallies won by S / all rallies"
    changed = MetricDictionary.parse(data)
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    lock["entries"]["AN-01"]["0.1"] = definition_digest(changed.entry("AN-01"))
    shown = _git("-C", str(repo), "show", "main:metrics.lock.json")
    assert shown.returncode == 0, shown.stderr
    previous = DefinitionLock.parse(json.loads(shown.stdout))
    assert version_bump_violations(changed, DefinitionLock.parse(lock), previous=previous) == (
        "AN-01 0.1: locked digest rewritten; the lock is append-only, bump the version",
    )
