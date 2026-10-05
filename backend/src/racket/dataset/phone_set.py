"""Phone fixture set entries and the R-05 upload-cap measurement (ST-025, NFR-025, FR-023 K12).

Pure domain code: probe facts arrive as data from the ffprobe adapter
(``scripts/fixtures/build_phone_manifest.py``). No I/O, no framework imports.

* A clip entry follows the QA seam in ``tests/support/contract.py`` (phones-v1) and adds the
  measured ``mb_per_minute``.
* VFR uses the product rule (``video_ingest.domain.media_facts``): real frame rate differs
  from the average frame rate.
* The cap assessment answers R-05: at the highest measured rate, which of the two caps
  (size or duration) a player hits first, and after how many minutes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Literal

MB = 1_000_000  # decimal megabytes, as phone makers and the upload copy use them
SUPPORTED_CODECS = frozenset({"h264", "hevc"})  # NFR-025


class RecordingError(ValueError):
    """The probe facts of a recording cannot be used for the set or the measurement."""


@dataclass(frozen=True)
class Recording:
    path: str
    device_model: str
    bytes: int
    duration_s: float
    container: str
    video_codec: str
    real_fps: Fraction
    avg_fps: Fraction
    width: int
    height: int
    shows_people: bool
    consent_record: str | None

    def __post_init__(self) -> None:
        if not self.device_model.strip():
            raise RecordingError(f"{self.path}: device_model must be named")
        if self.bytes <= 0:
            raise RecordingError(f"{self.path}: bytes must be positive")
        if self.duration_s <= 0:
            raise RecordingError(f"{self.path}: duration must be positive")
        if self.video_codec not in SUPPORTED_CODECS:
            raise RecordingError(f"{self.path}: unsupported codec {self.video_codec!r}")

    @property
    def vfr(self) -> bool:
        return self.real_fps != self.avg_fps

    @property
    def mb_per_minute(self) -> float:
        return self.bytes / MB / (self.duration_s / 60.0)


def clip_entry(rec: Recording) -> dict[str, Any]:
    """The manifest ``clips`` entry for one recording."""
    return {
        "path": rec.path,
        "device_model": rec.device_model,
        "fps": round(float(rec.real_fps), 3),  # nominal rate, as set on the phone
        "avg_fps": round(float(rec.avg_fps), 3),
        "vfr": rec.vfr,
        "container": rec.container,
        "video_codec": rec.video_codec,
        "width": rec.width,
        "height": rec.height,
        "duration_s": round(rec.duration_s, 3),
        "bytes": rec.bytes,
        "mb_per_minute": round(rec.mb_per_minute, 3),
        "shows_people": rec.shows_people,
        "consent_record": rec.consent_record,
    }


@dataclass(frozen=True)
class CapAssessment:
    max_bytes: int
    max_duration_s: float
    models: int
    break_even_mb_per_minute: float
    max_mb_per_minute: float
    worst_device_model: str
    worst_minutes_at_size_cap: float
    binding_cap: Literal["size", "duration"]


def assess_caps(
    recordings: Sequence[Recording], *, max_bytes: int, max_duration_s: float
) -> CapAssessment:
    """R-05: compare the measured MB/min with the rate at which both caps bind together."""
    if not recordings:
        raise RecordingError("the assessment needs at least one recording")
    max_minutes = max_duration_s / 60.0
    break_even = max_bytes / MB / max_minutes
    worst = max(recordings, key=lambda r: r.mb_per_minute)
    minutes_at_size_cap = max_bytes / MB / worst.mb_per_minute
    return CapAssessment(
        max_bytes=max_bytes,
        max_duration_s=max_duration_s,
        models=len({r.device_model for r in recordings}),
        break_even_mb_per_minute=break_even,
        max_mb_per_minute=worst.mb_per_minute,
        worst_device_model=worst.device_model,
        worst_minutes_at_size_cap=minutes_at_size_cap,
        binding_cap="size" if minutes_at_size_cap < max_minutes else "duration",
    )
