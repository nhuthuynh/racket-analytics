"""SEC-R1-01 regression (threat model T-WS-2 / F-2): an uploaded "video" that is really a
streaming manifest must not make ffprobe fetch other URLs (SSRF / LFI from the worker).

Boundary crossed: a real ffprobe child process reading over real HTTP. The manifest is served
at an extensionless key-like path (``/originals/<hex>``, as object keys are), so FFmpeg's
"non standard extension" guard does not help; only an input-format allowlist does. A canary
HTTP server counts every request the probe makes to it: the expected count is zero.
"""

from __future__ import annotations

import http.server
import shutil
import threading
from collections.abc import Iterator

import pytest

from racket.video_ingest.probe import ProbeFailed, ProbeLimits, ffprobe_bin, run_ffprobe

KEY_PATH = "/originals/0123456789abcdef0123456789abcdef"
QUERY = "?X-Amz-Expires=900&X-Amz-Signature=abc"
FAST = ProbeLimits(wall_clock_s=10, cpu_s=10, memory_bytes=512 * 1024**2)


class _Server:
    def __init__(self, body: bytes = b"") -> None:
        self.body = body
        self.paths: list[str] = []
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                outer.paths.append(self.path)
                self.send_response(200 if outer.body else 404)
                self.send_header("Content-Length", str(len(outer.body)))
                self.end_headers()
                self.wfile.write(outer.body)

            def log_message(self, *args: object) -> None:
                pass

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def __enter__(self) -> _Server:
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


def _dash(canary: str) -> bytes:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static" mediaPresentationDuration="PT2S"
     minBufferTime="PT1S" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011">
  <Period>
    <AdaptationSet contentType="video" mimeType="video/mp4">
      <Representation id="1" mimeType="video/mp4" bandwidth="1000" codecs="avc1.42c01e"
                      width="16" height="16">
        <BaseURL>{canary}/ssrf-dash.mp4</BaseURL>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
""".encode()


def _hls(canary: str) -> bytes:
    return (
        "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:2\n#EXT-X-MEDIA-SEQUENCE:0\n"
        f"#EXTINF:2.0,\n{canary}/ssrf-hls.ts\n#EXT-X-ENDLIST\n"
    ).encode()


@pytest.fixture
def canary() -> Iterator[_Server]:
    with _Server() as server:
        yield server


@pytest.mark.parametrize("manifest", [_dash, _hls], ids=["dash", "hls"])
def test_a_manifest_disguised_as_a_video_fetches_nothing(canary: _Server, manifest: object) -> None:
    if shutil.which(ffprobe_bin()) is None:
        pytest.fail(f"ffprobe binary not found: {ffprobe_bin()}", pytrace=False)
    with _Server(manifest(canary.base)) as origin:  # type: ignore[operator]
        with pytest.raises(ProbeFailed):
            run_ffprobe(origin.base + KEY_PATH + QUERY, limits=FAST)

        assert origin.paths == [KEY_PATH + QUERY]  # the original itself was read
    assert canary.paths == []  # and nothing else: no request reached the canary
