"""The metric dictionary ships inside the built backend package (ST-043; FR-102; NFR-075).

Integration (build + filesystem boundary): builds the real wheel with ``uv build`` and reads the
dictionary and its lock out of the archive, the way the API and worker images load them. A wheel
without ``metrics.json`` or with a stale ``metrics.lock.json`` would make the stats API fail
closed in production although every unit test passed against the source tree. No services needed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from racket.sports.pickleball.metrics import (
    LOCK_PATH,
    METRICS_PATH,
    MetricDictionary,
    definition_digest,
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
    for entry in dictionary.entries:
        assert lock["entries"][entry.id] == {
            "version": entry.version,
            "digest": definition_digest(entry),
        }, f"{entry.id}: packaged lock is stale"
    reviewed = {e.id for e in dictionary.entries if e.status in ("coach-reviewed", "verified")}
    assert {e.id for e in dictionary.published()} == reviewed
