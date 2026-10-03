"""SEC-R1-01 (threat model T-WS-2 / T-WS-3): ffprobe may only demux the MP4/MOV family.

Without an input-format allowlist ffprobe auto-detects the container, so a DASH or HLS manifest
uploaded as a "video" turns the worker into an HTTP client for any URL the uploader picks.
"""

from __future__ import annotations

from racket.video_ingest.probe import ffprobe_argv

URL = "http://objectstore:8333/racket-media/originals/abc?X-Amz-Signature=deadbeef"
MP4_FAMILY = "mov,mp4,m4a,3gp,3g2,mj2"


def test_streaming_manifest_demuxers_are_not_allowed() -> None:
    argv = ffprobe_argv("ffprobe", URL)

    assert "-format_whitelist" in argv
    allowed = set(argv[argv.index("-format_whitelist") + 1].split(","))
    assert not allowed & {
        "dash",
        "hls",
        "applehttp",
        "webm_dash_manifest",
        "concat",
        "image2",
        "tee",
        "data",
        "sdp",
        "rtsp",
    }


def test_the_input_format_allowlist_is_exactly_the_mp4_family() -> None:
    argv = ffprobe_argv("ffprobe", URL)

    assert argv[argv.index("-format_whitelist") + 1] == MP4_FAMILY
    assert argv.index("-format_whitelist") < argv.index(URL)  # an input option, before the URL
