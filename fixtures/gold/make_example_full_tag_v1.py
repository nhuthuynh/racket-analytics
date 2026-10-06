"""Build ``fixtures/gold/example-full-tag-v1``: the schema example of gold-set manifest v1.

ST-040 (FR-151). This is NOT an evaluation set. It holds five 2 s synthetic clips (FFmpeg
``testsrc2`` patterns, no people, CC0) and Full Tag label files that only exercise the schema:
venue split with 3 held-out venues, one double-labelled clip, no admitted shot facets (no
agreement was measured, so none is claimed). Evaluation code must not read it as gold.

Usage (from the repo root)::

    uv run --project backend python fixtures/gold/make_example_full_tag_v1.py
    cd backend && uv run racket-manifest-check ../fixtures/gold/example-full-tag-v1

Deterministic: bit-exact single-threaded encodes, so a rebuild gives the same sha256 values
(the manifest then needs no version bump).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

SET = Path(__file__).resolve().parent / "example-full-tag-v1"
FPS = 60
SECONDS = 2
FRAMES = FPS * SECONDS
# (clip number, synthetic venue, split); 3 held-out venues as QD-GD-04 requires.
CLIPS = [
    (1, "synthetic-venue-1", "train"),
    (2, "synthetic-venue-2", "train"),
    (3, "synthetic-venue-3", "test"),
    (4, "synthetic-venue-4", "test"),
    (5, "synthetic-venue-5", "test"),
]
DOUBLE_LABELLED = {1}


def encode(out: Path, n: int) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        sys.exit("ffmpeg is required")
    subprocess.run(  # noqa: S603 - fixed argv, no shell; writes a local fixture
        [
            ffmpeg,
            "-nostdin",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=320x180:rate={FPS}:duration={SECONDS}",
            "-vf",
            f"hue=h={n * 60}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "35",
            "-pix_fmt",
            "yuv420p",
            "-threads",
            "1",
            "-x264-params",
            "threads=1:sliced-threads=0",
            "-fflags",
            "+bitexact",
            "-flags:v",
            "+bitexact",
            "-map_metadata",
            "-1",
            "-movflags",
            "+faststart",
            str(out),
        ],
        check=True,
    )


def labels(n: int) -> dict[str, object]:
    """Schema-only labels: one counted rally and one replay, hits and a bounce."""
    return {
        "schema": "full-tag-labels/v1",
        "clip": f"clips/c{n}.mp4",
        "fps": FPS,
        "frame_count": FRAMES,
        "players": ["A1", "A2", "B1", "B2"],
        "rallies": [
            {
                "id": "r1",
                "start_frame": 6,
                "end_frame": 70,
                "outcome": {
                    "ending": "unforced_error",
                    "winning_side": "A",
                    "responsible_player": "B2",
                    "fault_kind": None,
                },
                "events": [
                    {"type": "hit", "frame": 10, "hitter": "A1", "facets": {}},
                    {"type": "bounce", "frame": 34, "visible": True, "court_xy_m": None},
                    {"type": "hit", "frame": 52, "hitter": "B2", "facets": {}},
                ],
            },
            {
                "id": "r2",
                "start_frame": 80,
                "end_frame": 110,
                "outcome": {
                    "ending": "replay",
                    "winning_side": None,
                    "responsible_player": None,
                    "fault_kind": None,
                },
                "events": [{"type": "hit", "frame": 84, "hitter": "B1", "facets": {}}],
            },
        ],
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if SET.exists():
        shutil.rmtree(SET)
    (SET / "clips").mkdir(parents=True)
    (SET / "labels").mkdir()
    clips = []
    for n, venue, _split in CLIPS:
        encode(SET / "clips" / f"c{n}.mp4", n)
        doc = json.dumps(labels(n), indent=2) + "\n"
        (SET / "labels" / f"c{n}.json").write_text(doc, encoding="utf-8")
        second = None
        if n in DOUBLE_LABELLED:
            second = f"labels/c{n}.second.json"
            (SET / second).write_text(doc, encoding="utf-8")
        clips.append(
            {
                "path": f"clips/c{n}.mp4",
                "label_file": f"labels/c{n}.json",
                "second_label_file": second,
                "venue_id": venue,
                "double_labelled": n in DOUBLE_LABELLED,
                "shows_people": False,
                "consent_record": None,
                "consent_jurisdiction": None,
            }
        )
    files = sorted(p for p in SET.rglob("*") if p.is_file())
    manifest = {
        "schema": "gold-set-manifest/v1",
        "id": "example-full-tag-v1",
        "version": 1,
        "created": "2026-10-06",
        "description": (
            "Schema example of gold-set manifest v1 and Full Tag labels v1 (ST-040). NOT an "
            "evaluation set: synthetic FFmpeg test patterns, schema-only labels, synthetic "
            "venues. Built by fixtures/gold/make_example_full_tag_v1.py."
        ),
        "purpose": "vision",
        "label_schema": "full-tag-labels/v1",
        "rules_version": None,
        "metric_dict_version": None,
        "licence": "CC0-1.0",
        "consent_status": "synthetic",
        "labellers": [{"role_id": "synthetic-generator", "role": "generator"}],
        "agreement": [],
        "venues": [{"id": venue, "split": split} for _n, venue, split in CLIPS],
        "clips": clips,
        "files": [
            {
                "path": p.relative_to(SET).as_posix(),
                "sha256": sha256(p),
                "bytes": p.stat().st_size,
            }
            for p in files
        ],
    }
    (SET / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {SET} ({len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
