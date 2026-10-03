"""MediaFacts.from_ffprobe (ST-009 unit used by the ST-007 probe stage; sprint-00 §5, in order).

An Anticorruption Layer over ffprobe's JSON: tool vocabulary in, Capture & Media facts out.
The fixture JSON is the committed ffprobe output of the synthetic clip (no I/O beyond reading it
once at import, which is test data, not the unit's behaviour).
"""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from racket.video_ingest.domain import InvalidProbeOutput, MediaFacts, NotAVideo
from tests.support.paths import SYNTHETIC_60S

FIXTURE: dict[str, Any] = json.loads((SYNTHETIC_60S / "ffprobe.json").read_text())


def probe(**changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(FIXTURE)
    for path, value in changes.items():
        target: Any = data
        *parents, leaf = path.split("__")
        for part in parents:
            target = target[int(part)] if part.isdigit() else target[part]
        if value is None:
            target.pop(leaf, None)
        else:
            target[leaf] = value
    return data


# 1. JSON with no video stream -> NotAVideo
def test_no_video_stream_is_not_a_video() -> None:
    data = probe()
    data["streams"] = [s for s in data["streams"] if s["codec_type"] != "video"]

    with pytest.raises(NotAVideo):
        MediaFacts.from_ffprobe(data)


def test_cover_art_alone_is_not_a_video() -> None:
    data = probe(streams__0__disposition={"attached_pic": 1})

    with pytest.raises(NotAVideo):
        MediaFacts.from_ffprobe(data)


# 2. missing duration -> error
def test_missing_duration_is_an_error() -> None:
    data = probe(format__duration=None, streams__0__duration=None)

    with pytest.raises(InvalidProbeOutput):
        MediaFacts.from_ffprobe(data)


@pytest.mark.parametrize("bad", [[], "garbage", {"streams": "x"}, {"streams": [1]}])
def test_malformed_json_is_an_error(bad: Any) -> None:
    with pytest.raises(InvalidProbeOutput):
        MediaFacts.from_ffprobe(bad)


# 3. r_frame_rate != avg_frame_rate -> vfr = True
def test_differing_frame_rates_mean_variable_frame_rate() -> None:
    facts = MediaFacts.from_ffprobe(probe(streams__0__avg_frame_rate="30000/1001"))

    assert facts.vfr is True
    assert facts.fps == pytest.approx(29.97)


# 4. a 1080p60 fixture JSON -> expected facts
def test_fixture_gives_the_expected_facts() -> None:
    facts = MediaFacts.from_ffprobe(FIXTURE)

    assert facts.duration_ms == 60000
    assert facts.fps == 60
    assert (facts.width, facts.height) == (1920, 1080)
    assert facts.has_audio is True
    assert facts.vfr is False
    assert facts.video_codec == "h264"
    assert facts.container == FIXTURE["format"]["format_name"]


def test_no_audio_stream_means_no_audio() -> None:
    data = probe()
    data["streams"] = [s for s in data["streams"] if s["codec_type"] == "video"]

    assert MediaFacts.from_ffprobe(data).has_audio is False
