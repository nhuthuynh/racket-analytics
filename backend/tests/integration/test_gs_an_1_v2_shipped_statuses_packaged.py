"""The built package ships the coach's statuses, so the stats API publishes AN-01..AN-07
(GS-AN-1-V2; ST-043 review round 2: PD-R2S3-01, PE-R2S3-05; FR-102; ADR 0044).

Integration (build + filesystem boundary): builds the real wheel with ``uv build`` and loads the
packaged ``metrics.json`` the way the API and worker images do. A source tree that mirrors the
coach while the wheel ships an older file would leave D-01 empty in production although every
unit test passed. Negative case first: a packaged entry the coach has not reviewed is reported.
No services needed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from racket.sports.pickleball.metrics import MetricDictionary
from tests.support.metric_status import mismatches, recorded_statuses

pytestmark = pytest.mark.integration

BACKEND = Path(__file__).resolve().parents[2]
MEMBER = "racket/sports/pickleball/metrics.json"
AN_01_TO_07 = [f"AN-0{i}" for i in range(1, 8)]


@pytest.fixture(scope="module")
def packaged(tmp_path_factory: pytest.TempPathFactory) -> MetricDictionary:
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
    with zipfile.ZipFile(built) as wheel:
        return MetricDictionary.parse(json.loads(wheel.read(MEMBER)))


def test_a_packaged_status_the_coach_did_not_record_is_reported(
    packaged: MetricDictionary,
) -> None:
    """Negative first: the packaged statuses with AN-05 set back to draft differ from the
    record, and the comparison names that entry and both values."""
    shipped = {e.id: e.status for e in packaged.entries} | {"AN-05": "draft"}
    recorded = recorded_statuses()
    assert recorded["AN-05"] == "coach-reviewed"
    assert "AN-05: shipped 'draft', recorded 'coach-reviewed'" in mismatches(shipped, recorded)


def test_the_packaged_statuses_equal_the_coachs_record(packaged: MetricDictionary) -> None:
    shipped = {e.id: e.status for e in packaged.entries}
    assert mismatches(shipped, recorded_statuses()) == []


def test_the_packaged_dictionary_publishes_an_01_to_an_07(packaged: MetricDictionary) -> None:
    assert [e.id for e in packaged.published()] == AN_01_TO_07
    assert {e.status for e in packaged.entries} == {"coach-reviewed"}
