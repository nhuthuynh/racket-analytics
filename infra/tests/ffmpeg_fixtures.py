"""Fixtures for CI-FFMPEG: a small archive with the pinned BtbN layout, a pin file for it, and a
local HTTP source on 127.0.0.1 that serves it normally, stalls, or serves different bytes.

The archive holds shell stand-ins for `bin/ffmpeg` and `bin/ffprobe`, so no real build is
downloaded or run by the tests.
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

NAME = "ffmpeg-n0.0-test-linux64-lgpl-0.0"
TAG = "autobuild-test"
FILES = {
    "bin/ffmpeg": b"#!/bin/sh\necho 'ffmpeg version n0.0-test'\n",
    "bin/ffprobe": b"#!/bin/sh\necho 'ffprobe version n0.0-test'\n",
    "LICENSE.txt": b"GNU LESSER GENERAL PUBLIC LICENSE (test stand-in)\n",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_archive(files: dict[str, bytes] = FILES, name: str = NAME) -> bytes:
    """A tar.xz with `<name>/<rel>` members plus a decoy, like the BtbN release archives."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as tar:
        for rel, data in {"doc/readme.html": b"<p>decoy</p>", **files}.items():
            info = tarfile.TarInfo(f"{name}/{rel}")
            info.size = len(data)
            info.mode = 0o755 if rel.startswith("bin/") else 0o644
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


ARCHIVE = build_archive()


def write_pin(path: Path, sources: list[str], archive: bytes = ARCHIVE) -> Path:
    pin = {
        "schema": "ffmpeg-pin/v1",
        "tag": TAG,
        "name": NAME,
        "archive_sha256": sha256(archive),
        "sources": sources,
        "files": {rel: sha256(data) for rel, data in FILES.items()},
        "licence": "test stand-in",
    }
    path.write_text(json.dumps(pin, indent=2) + "\n")
    return path


def fill_install_dir(dest: Path) -> None:
    """The pinned build as the Actions cache restores it."""
    for rel, data in FILES.items():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755 if rel.startswith("bin/") else 0o644)


@dataclass
class Source:
    """One download source. mode: 'ok', 'stall' (trickles one byte every 0.2 s) or 'other'."""

    mode: str = "ok"
    requests: list[str] = field(default_factory=list)


@contextmanager
def serve(sources: dict[str, Source]) -> Iterator[str]:
    """Serve each source under `/<key>/...`; yields the base URL."""
    stop = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: object) -> None:
            return

        def do_GET(self) -> None:
            key = self.path.strip("/").split("/", 1)[0]
            source = sources.get(key)
            if source is None:
                self.send_error(404)
                return
            source.requests.append(self.path)
            body = ARCHIVE
            if source.mode == "other":
                body = build_archive({**FILES, "bin/ffprobe": b"tampered"})
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                if source.mode == "stall":
                    for i in range(len(body)):
                        if stop.is_set():
                            return
                        self.wfile.write(body[i : i + 1])
                        self.wfile.flush()
                        time.sleep(0.2)
                else:
                    self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
