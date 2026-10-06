#!/usr/bin/env bash
# Generate a large, valid phone-like video for the live upload-throughput run (goal scorecard
# G01-05, NFR-016b). Not committed: it is written to a scratch path and is >= 1 GB.
#
#   1920x1080, 60 fps, H.264 at a constant ~70 Mbit/s (FFmpeg "testsrc2", no people), AAC
#   stereo. Default 120 s -> about 1.05 GB, well inside the 10 GB / 150 min caps (FR-023).
#
# Usage: scripts/measure/make_large_fixture.sh OUTPUT.mp4 [SECONDS]
set -euo pipefail
out="${1:?usage: make_large_fixture.sh OUTPUT.mp4 [SECONDS]}"
secs="${2:-120}"
command -v ffmpeg >/dev/null || { echo "ffmpeg not found" >&2; exit 127; }
mkdir -p "$(dirname "$out")"
ffmpeg -nostdin -hide_banner -loglevel error -y \
  -f lavfi -i "testsrc2=size=1920x1080:rate=60:duration=${secs}" \
  -f lavfi -i "sine=frequency=1000:sample_rate=48000:duration=${secs}" \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -preset ultrafast -pix_fmt yuv420p \
  -b:v 70M -minrate 70M -maxrate 70M -bufsize 70M -x264-params nal-hrd=cbr \
  -c:a aac -b:a 128k -ac 2 -movflags +faststart "$out"
size=$(stat -c %s "$out")
echo "$out $size bytes"
[ "$size" -ge 1000000000 ] || { echo "fixture is below 1 GB; pass more SECONDS" >&2; exit 1; }
