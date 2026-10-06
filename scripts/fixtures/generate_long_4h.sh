#!/usr/bin/env bash
# Generate the "4-hour video" fixture for upload validation (ST-018, IT-01-09, sprint-01 §7.5).
#
#   4 h (14,400 s), 64x64, 1 fps constant frame rate, H.264 (yuv420p), no audio, ~200 KB.
#   A real, playable MP4 whose duration is above the provisional 150-minute cap (FR-023, K12),
#   so the probe reads a true duration instead of a patched header. Black frames: no people.
#
# Deterministic for a given FFmpeg build (single thread, bitexact, no metadata). The file is
# committed and frozen by fixtures/clips/long-4h/manifest.json; regenerating it with another
# build is a new version of the set.
#
# Usage: scripts/fixtures/generate_long_4h.sh [OUTPUT_DIR]   (default fixtures/clips/long-4h)
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
out_dir="${1:-$repo/fixtures/clips/long-4h}"
mkdir -p "$out_dir"
tmp="$out_dir/.clip.mp4.partial"
trap 'rm -f "$tmp"' EXIT

command -v ffmpeg >/dev/null || { echo "ffmpeg not found" >&2; exit 127; }

ffmpeg -nostdin -hide_banner -loglevel error -y \
  -f lavfi -i "color=c=black:size=64x64:rate=1:duration=14400" \
  -c:v libx264 -preset ultrafast -pix_fmt yuv420p -g 600 -threads 1 \
  -x264-params "threads=1:lookahead-threads=1:sliced-threads=0" \
  -map_metadata -1 -map_chapters -1 \
  -fflags +bitexact -flags:v +bitexact \
  -movflags +faststart \
  -f mp4 "$tmp"
mv "$tmp" "$out_dir/clip.mp4"
echo "wrote $out_dir/clip.mp4"
