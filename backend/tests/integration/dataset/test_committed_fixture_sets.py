"""Every committed fixture/gold set is intact (FR-151, NFR-078), and the synthetic clip has the
properties ST-011 requires: 60 s, 1920x1080 at 60 fps CFR, H.264 + AAC (checked with ffprobe)."""

from __future__ import annotations

import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

import pytest

from racket.dataset.filesystem import hash_set, load_manifest
from racket.dataset.manifest import ManifestCheck
from tests.support.paths import FIXTURES, SYNTHETIC_60S, SYNTHETIC_CLIP

pytestmark = pytest.mark.integration

MAX_COMMITTED_BYTES = 15 * 1024 * 1024


def _sets() -> list[Path]:
    return sorted(p.parent for p in FIXTURES.rglob("manifest.json"))


def test_there_is_at_least_one_set() -> None:
    assert SYNTHETIC_60S in _sets()


@pytest.mark.parametrize("set_dir", _sets(), ids=lambda p: str(p.relative_to(FIXTURES)))
def test_committed_set_matches_its_manifest(set_dir: Path) -> None:
    manifest = load_manifest(set_dir / "manifest.json")

    result = ManifestCheck.check(manifest, hash_set(set_dir))

    assert result.passed, [p.describe() for p in result.problems]
    assert manifest.consent_status in {"synthetic", "consented"}


def test_committed_clip_is_under_the_size_limit() -> None:
    assert SYNTHETIC_CLIP.stat().st_size < MAX_COMMITTED_BYTES


def test_synthetic_clip_has_the_required_properties() -> None:
    ffprobe = shutil.which("ffprobe")
    assert ffprobe, "ffprobe is required for this check"
    expected = json.loads((SYNTHETIC_60S / "manifest.json").read_text())["expected_media_facts"]
    out = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(SYNTHETIC_CLIP),
        ],
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    probe = json.loads(out)
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    audio = [s for s in probe["streams"] if s["codec_type"] == "audio"]

    assert round(float(probe["format"]["duration"]) * 1000) == expected["duration_ms"] == 60_000
    assert (video["width"], video["height"]) == (1920, 1080)
    assert Fraction(video["r_frame_rate"]) == Fraction(video["avg_frame_rate"]) == 60
    assert video["codec_name"] == expected["video_codec"] == "h264"
    assert [a["codec_name"] for a in audio] == ["aac"]
    assert int(video["nb_frames"]) == expected["frame_count"]
