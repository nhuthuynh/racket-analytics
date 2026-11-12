"""A local stand-in for the media bucket that ``scripts/ops/backup.py`` mirrors (ST-076a;
ADR 0058 rule 1, artefact ``objects.tar.age``). Real HTTP on 127.0.0.1, so the script runs as a
subprocess exactly as in the ``backup`` service.

It answers ``ListObjectsV2`` (one key a page, so continuation tokens are followed) and object
``GET``s on one bucket, refuses a request without a SigV4 ``Authorization`` header (403) and any
method other than ``GET`` (405), and records every request so a test can assert the mirror only
reads.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit
from xml.sax.saxutils import escape

BUCKET = "racket-media"
NS = "http://s3.amazonaws.com/doc/2006-03-01/"


@dataclass
class FakeS3:
    objects: dict[str, bytes]
    url: str = ""
    requests: list[tuple[str, str]] = field(default_factory=list)

    def env(self) -> dict[str, str]:
        """The variables the Compose ``backup`` service sets (made-up keys, never real ones)."""
        return {
            "S3_ENDPOINT_URL": self.url,
            "S3_BUCKET_MEDIA": BUCKET,
            "S3_REGION": "us-east-1",
            "BACKUP_S3_ACCESS_KEY_ID": "fake-backup-key",
            "BACKUP_S3_SECRET_ACCESS_KEY": "fake-backup-secret",
        }


def _listing(stub: FakeS3, token: str | None) -> bytes:
    keys = sorted(stub.objects)
    start = int(token) if token else 0
    page, nxt = keys[start : start + 1], start + 1
    more = nxt < len(keys)
    contents = "".join(
        f"<Contents><Key>{escape(k)}</Key><Size>{len(stub.objects[k])}</Size></Contents>"
        for k in page
    )
    tail = f"<NextContinuationToken>{nxt}</NextContinuationToken>" if more else ""
    return (
        f'<ListBucketResult xmlns="{NS}">{contents}'
        f"<IsTruncated>{'true' if more else 'false'}</IsTruncated>{tail}</ListBucketResult>"
    ).encode()


def _handler(stub: FakeS3) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: object) -> None:
            pass

        def _refuse(self, status: int) -> None:
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self) -> None:
            stub.requests.append(("GET", self.path))
            if not self.headers.get("Authorization", "").startswith("AWS4-HMAC-SHA256 "):
                return self._refuse(403)
            u = urlsplit(self.path)
            q = parse_qs(u.query)
            if u.path.rstrip("/") == f"/{BUCKET}" and q.get("list-type") == ["2"]:
                token = q.get("continuation-token")
                body = _listing(stub, token[0] if token else None)
            elif u.path.startswith(f"/{BUCKET}/") and unquote(u.path[len(BUCKET) + 2 :]) in (
                stub.objects
            ):
                body = stub.objects[unquote(u.path[len(BUCKET) + 2 :])]
            else:
                return self._refuse(404)
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return None

        def _not_allowed(self) -> None:
            stub.requests.append((self.command, self.path))
            self._refuse(405)

        do_PUT = do_POST = do_DELETE = do_HEAD = _not_allowed

    return Handler


@contextmanager
def serve(objects: dict[str, bytes]) -> Iterator[FakeS3]:
    stub = FakeS3(objects)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(stub))
    stub.url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield stub
    finally:
        server.shutdown()
        server.server_close()
