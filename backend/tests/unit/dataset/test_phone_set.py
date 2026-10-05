"""Phone fixture set: clip entries and the R-05 upload-cap measurement (ST-025, FR-023 K12).

Pure domain: probe facts come in as data (the ffprobe adapter is scripts/fixtures/).
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from racket.dataset.phone_set import (
    CapAssessment,
    Recording,
    RecordingError,
    assess_caps,
    clip_entry,
)

pytestmark = pytest.mark.unit

GB = 1_000_000_000
CAPS = {"max_bytes": 10 * GB, "max_duration_s": 150 * 60}


def a_recording(**overrides: object) -> Recording:
    values: dict[str, object] = {
        "path": "pixel-8/clip.mp4",
        "device_model": "Pixel 8",
        "bytes": 120_000_000,
        "duration_s": 60.0,
        "container": "mov,mp4,m4a,3gp,3g2,mj2",
        "video_codec": "h264",
        "real_fps": Fraction(60),
        "avg_fps": Fraction(60),
        "width": 1920,
        "height": 1080,
        "shows_people": False,
        "consent_record": None,
    }
    values.update(overrides)
    return Recording(**values)  # type: ignore[arg-type]


# --- negative cases first -------------------------------------------------------------


@pytest.mark.parametrize("duration", [0.0, -1.0])
def test_recording_with_no_duration_is_refused(duration: float) -> None:
    with pytest.raises(RecordingError, match="duration"):
        a_recording(duration_s=duration)


def test_recording_with_no_bytes_is_refused() -> None:
    with pytest.raises(RecordingError, match="bytes"):
        a_recording(bytes=0)


def test_recording_with_unsupported_codec_is_refused() -> None:
    with pytest.raises(RecordingError, match="codec"):
        a_recording(video_codec="vp9")


def test_recording_with_no_device_model_is_refused() -> None:
    with pytest.raises(RecordingError, match="device_model"):
        a_recording(device_model=" ")


def test_assessment_needs_at_least_one_recording() -> None:
    with pytest.raises(RecordingError):
        assess_caps([], **CAPS)


# --- behaviour --------------------------------------------------------------------------


def test_vfr_uses_the_product_rule_real_rate_differs_from_average() -> None:
    assert a_recording(real_fps=Fraction(60), avg_fps=Fraction(5994, 100)).vfr is True
    assert a_recording(real_fps=Fraction(60), avg_fps=Fraction(60)).vfr is False


def test_megabytes_per_minute_uses_decimal_megabytes() -> None:
    assert a_recording(bytes=120_000_000, duration_s=60.0).mb_per_minute == pytest.approx(120.0)
    assert a_recording(bytes=30_000_000, duration_s=30.0).mb_per_minute == pytest.approx(60.0)


def test_clip_entry_has_the_contract_fields() -> None:
    entry = clip_entry(a_recording(real_fps=Fraction(30000, 1001), avg_fps=Fraction(29)))

    assert entry["path"] == "pixel-8/clip.mp4"
    assert entry["device_model"] == "Pixel 8"
    assert entry["fps"] == pytest.approx(29.97, abs=0.01)
    assert entry["vfr"] is True
    assert entry["shows_people"] is False
    assert entry["consent_record"] is None
    assert entry["mb_per_minute"] == pytest.approx(120.0)


def test_break_even_rate_for_10_gb_and_150_minutes() -> None:
    result = assess_caps([a_recording()], **CAPS)

    assert isinstance(result, CapAssessment)
    # 10 GB over 150 min = 66.67 MB per minute (8.89 Mbit/s) before the size cap binds first.
    assert result.break_even_mb_per_minute == pytest.approx(66.667, abs=0.001)


def test_size_cap_binds_first_when_a_phone_records_above_break_even() -> None:
    heavy = a_recording(bytes=120_000_000, duration_s=60.0)  # 120 MB/min

    result = assess_caps([heavy], **CAPS)

    assert result.binding_cap == "size"
    assert result.worst_minutes_at_size_cap == pytest.approx(83.333, abs=0.001)
    assert result.worst_device_model == "Pixel 8"


def test_duration_cap_binds_when_every_phone_records_below_break_even() -> None:
    light = a_recording(bytes=50_000_000, duration_s=60.0)  # 50 MB/min

    result = assess_caps([light], **CAPS)

    assert result.binding_cap == "duration"
    assert result.worst_minutes_at_size_cap == pytest.approx(200.0)


def test_worst_case_is_the_highest_rate_across_models() -> None:
    a = a_recording(device_model="A", bytes=50_000_000)
    b = a_recording(device_model="B", path="b/clip.mov", bytes=100_000_000)

    result = assess_caps([a, b], **CAPS)

    assert result.worst_device_model == "B"
    assert result.max_mb_per_minute == pytest.approx(100.0)
    assert result.models == 2
