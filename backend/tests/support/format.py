"""How the UI renders API values, so API-level scenarios can assert the user-visible text.
Mirrors the front end's formatDuration (sprint-00 §5 Vitest units)."""

from __future__ import annotations

from typing import Any

from tests.support.contract import STATUS_LABELS


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, f"<unknown status {status!r}>")


def format_duration(ms: int) -> str:
    if ms < 0:
        raise ValueError("negative duration")
    total = round(ms / 1000)
    hours, rest = divmod(total, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


def facts_display(media: dict[str, Any]) -> tuple[str, str, str]:
    fps = media["fps"]
    fps_text = f"{fps:g} fps" if isinstance(fps, (int, float)) else f"{fps} fps"
    return (
        format_duration(int(media["duration_ms"])),
        fps_text,
        f"{media['width']}×{media['height']}",
    )
