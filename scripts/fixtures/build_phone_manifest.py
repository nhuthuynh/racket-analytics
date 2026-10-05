"""Build a phone fixture-set manifest and the R-05 upload-cap measurement (ST-025).

Usage (from the repository root)::

    uv run --project backend python scripts/fixtures/build_phone_manifest.py SET_DIR \
        --id phones-v1 --version 1 --licence CC-BY-4.0 --consent-status consented \
        [--max-bytes 10000000000] [--max-duration-s 9000] [--r05-out r05.json]

SET_DIR holds the video files and ``recordings.csv`` with the columns
``path,device_model,shows_people,consent_record`` (one row per video; ``shows_people`` is
``true``/``false``; an empty ``consent_record`` means none). Each video is probed with
ffprobe, hashed, and written as a ``clips`` entry (contract seam phones-v1). The R-05
assessment (MB per minute per model, break-even rate, which cap binds first) is printed as
JSON and optionally written to ``--r05-out``. The manifest is checked by
``racket-manifest-check`` afterwards; a file with people and no consent record fails there.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

from racket.dataset.filesystem import MANIFEST_NAME, hash_set
from racket.dataset.phone_set import Recording, assess_caps, clip_entry

VIDEO_SUFFIXES = {".mp4", ".mov"}
CSV_NAME = "recordings.csv"


def _fraction(text: str) -> Fraction:
    num, _, den = text.partition("/")
    return Fraction(int(num), int(den or 1)) if den != "0" else Fraction(0)


def probe(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise SystemExit("ffprobe not found")
    out = subprocess.run(  # noqa: S603 - fixed argv, no shell; the path is a local fixture
        [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    data: dict[str, Any] = json.loads(out.stdout)
    return data


def recording(set_dir: Path, row: dict[str, str]) -> Recording:
    path = set_dir / row["path"]
    facts = probe(path)
    video = next(s for s in facts["streams"] if s.get("codec_type") == "video")
    consent = (row.get("consent_record") or "").strip() or None
    return Recording(
        path=row["path"],
        device_model=row["device_model"],
        bytes=path.stat().st_size,
        duration_s=float(facts["format"]["duration"]),
        container=facts["format"]["format_name"],
        video_codec=video["codec_name"],
        real_fps=_fraction(video["r_frame_rate"]),
        avg_fps=_fraction(video["avg_frame_rate"]),
        width=int(video["width"]),
        height=int(video["height"]),
        shows_people=row["shows_people"].strip().lower() == "true",
        consent_record=consent,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("set_dir", type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--version", type=int, required=True)
    parser.add_argument("--licence", required=True)
    parser.add_argument("--consent-status", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--created", default="")
    parser.add_argument("--max-bytes", type=int, default=10_000_000_000)
    parser.add_argument("--max-duration-s", type=float, default=9000.0)
    parser.add_argument("--r05-out", type=Path)
    args = parser.parse_args(argv)

    set_dir: Path = args.set_dir
    with (set_dir / CSV_NAME).open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    on_disk = sorted(
        p.relative_to(set_dir).as_posix()
        for p in set_dir.rglob("*")
        if p.suffix.lower() in VIDEO_SUFFIXES
    )
    listed = sorted(r["path"] for r in rows)
    if on_disk != listed:
        print(f"FAIL {CSV_NAME} does not list exactly the videos: {on_disk} vs {listed}")
        return 1

    recordings = [recording(set_dir, r) for r in rows]
    hashes = hash_set(set_dir)
    manifest = {
        "id": args.id,
        "version": args.version,
        "created": args.created,
        "description": args.description,
        "licence": args.licence,
        "consent_status": args.consent_status,
        "split": "fixture",
        "generator": {"script": "scripts/fixtures/build_phone_manifest.py"},
        "files": [
            {"path": p, "sha256": h, "bytes": (set_dir / p).stat().st_size}
            for p, h in sorted(hashes.items())
        ],
        "clips": [clip_entry(r) for r in sorted(recordings, key=lambda r: r.path)],
    }
    (set_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", "utf-8")

    assessment = dataclasses.asdict(
        assess_caps(recordings, max_bytes=args.max_bytes, max_duration_s=args.max_duration_s)
    )
    assessment["per_clip"] = [
        {"path": r.path, "device_model": r.device_model, "mb_per_minute": round(r.mb_per_minute, 3)}
        for r in recordings
    ]
    text = json.dumps(assessment, indent=2) + "\n"
    if args.r05_out:
        args.r05_out.write_text(text, "utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
