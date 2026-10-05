"""IT-00-09 (worker <-> object store, ST-009): the probe stage on the synthetic fixture
records 60 s, 60 fps, 1920x1080 and audio present (FR-081, FR-025)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from tests.support import contract
from tests.support.api import ApiDriver
from tests.support.flows import create_match, upload_fixture
from tests.support.paths import SYNTHETIC_60S

pytestmark = pytest.mark.slow


def test_probe_records_the_fixture_facts(api: ApiDriver, committed_db: Any) -> None:
    expected = json.loads((SYNTHETIC_60S / "manifest.json").read_text())["expected_media_facts"]
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "IT-00-09"))
    api.run(upload_fixture(ivy, match_id))

    assert contract.WORKER_RUN_UNTIL_IDLE.load()() >= 1

    media = api.request("ivy", "GET", contract.MATCH_MEDIA.format(match_id=match_id)).json()
    assert media["duration_ms"] == pytest.approx(expected["duration_ms"], abs=50)
    assert media["fps"] == expected["fps"]
    assert (media["width"], media["height"]) == (expected["width"], expected["height"])
    assert media["has_audio"] is True
    assert media["vfr"] is False
    assert media["video_codec"] == expected["video_codec"]
