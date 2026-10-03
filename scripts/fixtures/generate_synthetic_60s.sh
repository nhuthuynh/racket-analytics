#!/usr/bin/env bash
# Generate the synthetic 60-second fixture clip (ST-011, NFR-025, QD-GD-07).
#
#   60 s, 1920x1080, 60 fps constant frame rate, H.264 (yuv420p) + AAC-LC stereo 48 kHz.
#   Video: FFmpeg "testsrc" pattern (colour bars, moving gradient, running counter; no people -> no consent issue).
#   Audio: 1 kHz tone bursts of 80 ms at every whole second (a stand-in for paddle hits),
#          silence in between.
#
# Output is deterministic for a given FFmpeg build: single-threaded encode, bitexact flags,
# no metadata, fixed GOP. Different FFmpeg builds may produce different bytes, so the clip
# is committed and frozen by fixtures/clips/synthetic-60s/manifest.json; regenerating it
# with another build is a *new version* of the set (bump "version" in the manifest).
#
# Usage: scripts/fixtures/generate_synthetic_60s.sh [OUTPUT_DIR]
#        (default OUTPUT_DIR: fixtures/clips/synthetic-60s)
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
out_dir="${1:-$repo/fixtures/clips/synthetic-60s}"
mkdir -p "$out_dir"
tmp="$out_dir/.clip.mp4.partial"
trap 'rm -f "$tmp"' EXIT

command -v ffmpeg >/dev/null || { echo "ffmpeg not found" >&2; exit 127; }

ffmpeg -nostdin -hide_banner -loglevel error -y \
  -f lavfi -i "testsrc=size=1920x1080:rate=60:duration=60" \
  -f lavfi -i "aevalsrc=exprs='if(lt(mod(t\,1)\,0.08)\,0.5*sin(2*PI*1000*t)\,0)':s=48000:c=stereo:d=60" \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -preset veryfast -crf 28 -pix_fmt yuv420p -profile:v high -level:v 4.2 \
  -g 60 -keyint_min 60 -sc_threshold 0 -threads 1 \
  -x264-params "threads=1:lookahead-threads=1:sliced-threads=0" \
  -r 60 -fps_mode cfr \
  -c:a aac -b:a 128k -ar 48000 -ac 2 \
  -map_metadata -1 -map_chapters -1 \
  -fflags +bitexact -flags:v +bitexact -flags:a +bitexact \
  -movflags +faststart \
  -t 60 \
  -f mp4 "$tmp"

mv "$tmp" "$out_dir/clip.mp4"
trap - EXIT
echo "wrote $out_dir/clip.mp4 ($(stat -c %s "$out_dir/clip.mp4") bytes, sha256 $(sha256sum "$out_dir/clip.mp4" | cut -d' ' -f1))"
