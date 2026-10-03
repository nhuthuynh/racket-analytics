"""``MediaFacts``: what the probe stage learns about a stored video (sprint-00 §5; FR-025).

``from_ffprobe`` is an Anticorruption Layer over ffprobe's JSON [EP/ENG-13]: it accepts only
the fields it needs, validates them, and refuses anything that is not a video.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from racket.platform.errors import ValidationFailed


class InvalidProbeOutput(ValidationFailed):
    pass


class NotAVideo(InvalidProbeOutput):
    pass


def _rate(value: Any) -> Fraction | None:
    try:
        rate = Fraction(str(value))
    except (ValueError, ZeroDivisionError):
        return None
    return rate if rate > 0 else None


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InvalidProbeOutput(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True)
class MediaFacts:
    container: str
    video_codec: str
    duration_ms: int
    fps: float
    vfr: bool
    width: int
    height: int
    has_audio: bool

    @classmethod
    def from_ffprobe(cls, data: Any) -> MediaFacts:
        if not isinstance(data, dict) or not isinstance(data.get("streams"), list):
            raise InvalidProbeOutput("not ffprobe JSON")
        streams = data["streams"]
        if not all(isinstance(s, dict) for s in streams):
            raise InvalidProbeOutput("malformed stream list")
        raw_format = data.get("format")
        fmt: dict[str, Any] = raw_format if isinstance(raw_format, dict) else {}
        videos = [
            s
            for s in streams
            if s.get("codec_type") == "video"
            and not (s.get("disposition") or {}).get("attached_pic")
        ]
        if not videos:
            raise NotAVideo("no video stream")
        video = videos[0]

        avg = _rate(video.get("avg_frame_rate"))
        real = _rate(video.get("r_frame_rate"))
        if avg is None:
            raise InvalidProbeOutput("no average frame rate")

        duration_raw = fmt.get("duration") or video.get("duration")
        try:
            seconds = float(duration_raw)
        except (TypeError, ValueError):
            raise InvalidProbeOutput("no duration") from None
        if seconds < 0:
            raise InvalidProbeOutput("negative duration")

        return cls(
            container=str(fmt.get("format_name") or "unknown"),
            video_codec=str(video.get("codec_name") or "unknown"),
            duration_ms=round(seconds * 1000),
            fps=round(float(avg), 3),
            vfr=real is None or real != avg,
            width=_positive_int(video.get("width"), "width"),
            height=_positive_int(video.get("height"), "height"),
            has_audio=any(s.get("codec_type") == "audio" for s in streams),
        )
