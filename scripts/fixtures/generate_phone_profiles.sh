#!/usr/bin/env bash
# Generate the synthetic phone-PROFILE set (ST-025, NFR-025): short clips that reproduce the
# container/codec/frame-rate shapes phones write (H.264 MP4, HEVC MOV with the hvc1 tag,
# HEVC Main10, rotation metadata, a VFR file, a file without audio).
#
# These are NOT phone recordings. They come from FFmpeg lavfi test sources (no people, CC0)
# and exist so the probe and the validation can be tested against the shapes now. Their
# bitrates say nothing about real phones, so they are never used for the R-05 cap
# measurement: that needs real recordings in fixtures/clips/phones-v1 (see
# docs/data/phone-fixtures.md).
#
# Output is frozen by fixtures/clips/phone-profiles-v1/manifest.json, built with
# scripts/fixtures/build_phone_manifest.py. Another FFmpeg build may produce other bytes:
# regenerating is a new version of the set.
#
# Usage: scripts/fixtures/generate_phone_profiles.sh [OUTPUT_DIR]
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
out="${1:-$repo/fixtures/clips/phone-profiles-v1}"
mkdir -p "$out"
command -v ffmpeg >/dev/null || { echo "ffmpeg not found" >&2; exit 127; }

D=2  # seconds per clip
common=(-nostdin -hide_banner -loglevel error -y)
det=(-threads 1 -map_metadata -1 -map_chapters -1 -fflags +bitexact -flags:v +bitexact -flags:a +bitexact)
tone() { echo "sine=frequency=1000:sample_rate=48000:duration=$D"; }
x264=(-c:v libx264 -preset veryfast -crf 35 -pix_fmt yuv420p -x264-params "threads=1:lookahead-threads=1")
x265=(-c:v libx265 -preset veryfast -crf 35 -tag:v hvc1)
aac=(-c:a aac -b:a 64k -ar 48000 -ac 1)

# 1. H.264 MP4 1080p30 CFR + AAC
ffmpeg "${common[@]}" -f lavfi -i "testsrc2=size=1920x1080:rate=30:duration=$D" -f lavfi -i "$(tone)" \
  "${x264[@]}" -g 30 "${aac[@]}" -r 30 -fps_mode cfr "${det[@]}" -movflags +faststart \
  "$out/h264-mp4-1080p30.mp4"

# 2. H.264 MP4 1080p60 CFR + AAC
ffmpeg "${common[@]}" -f lavfi -i "testsrc2=size=1920x1080:rate=60:duration=$D" -f lavfi -i "$(tone)" \
  "${x264[@]}" -g 60 "${aac[@]}" -r 60 -fps_mode cfr "${det[@]}" -movflags +faststart \
  "$out/h264-mp4-1080p60.mp4"

# 3. HEVC MOV 1080p60 (hvc1) + AAC, stored landscape with a 90 degree display matrix
#    (a phone held upright). Encode, then remux with -display_rotation (an input option).
ffmpeg "${common[@]}" -f lavfi -i "testsrc2=size=1920x1080:rate=60:duration=$D" -f lavfi -i "$(tone)" \
  "${x265[@]}" -x265-params "pools=1:frame-threads=1:log-level=error" "${aac[@]}" -r 60 -fps_mode cfr \
  "${det[@]}" -f mov "$out/.rotated.partial.mov"
ffmpeg "${common[@]}" -display_rotation:v:0 90 -i "$out/.rotated.partial.mov" -map 0 -c copy \
  "${det[@]}" -f mov "$out/hevc-mov-1080p60-rotated.mov"
rm -f "$out/.rotated.partial.mov"

# 4. HEVC Main10 MOV 2160p30 + AAC (the shape of HDR recordings; no HDR signalling claimed)
ffmpeg "${common[@]}" -f lavfi -i "testsrc2=size=3840x2160:rate=30:duration=$D" -f lavfi -i "$(tone)" \
  "${x265[@]}" -pix_fmt yuv420p10le -x265-params "pools=1:frame-threads=1:log-level=error" \
  "${aac[@]}" -r 30 -fps_mode cfr "${det[@]}" -f mov "$out/hevc10-mov-2160p30.mov"

# 5. H.264 MP4 1080p VFR + AAC: 60 fps source, frames dropped in an irregular pattern and the
#    original timestamps kept, so the real and the average frame rates differ (product VFR rule).
ffmpeg "${common[@]}" -f lavfi -i "testsrc2=size=1920x1080:rate=60:duration=$D" -f lavfi -i "$(tone)" \
  -vf "select='not(eq(mod(n\,7)\,3))*not(eq(mod(n\,11)\,5))'" "${x264[@]}" "${aac[@]}" \
  -fps_mode vfr -enc_time_base 1/600 "${det[@]}" -movflags +faststart "$out/h264-mp4-1080p-vfr.mp4"

# 6. H.264 MOV 720p30, no audio track
ffmpeg "${common[@]}" -f lavfi -i "testsrc2=size=1280x720:rate=30:duration=$D" \
  "${x264[@]}" -g 30 -r 30 -fps_mode cfr "${det[@]}" -f mov "$out/h264-mov-720p30-noaudio.mov"

cat > "$out/recordings.csv" <<'CSV'
path,device_model,shows_people,consent_record
h264-mov-720p30-noaudio.mov,synthetic-profile/h264-mov-720p30-noaudio,false,
h264-mp4-1080p-vfr.mp4,synthetic-profile/h264-mp4-1080p-vfr,false,
h264-mp4-1080p30.mp4,synthetic-profile/h264-mp4-1080p30,false,
h264-mp4-1080p60.mp4,synthetic-profile/h264-mp4-1080p60,false,
hevc-mov-1080p60-rotated.mov,synthetic-profile/hevc-mov-1080p60-rotated,false,
hevc10-mov-2160p30.mov,synthetic-profile/hevc10-mov-2160p30,false,
CSV

ls -l "$out"
