"""Media route response headers on the web origin (SEC-S2-TM-03, QA-RV2-08; review round 2).

Media is served on the app origin (SRE-MEDIA, ADR 0029). SeaweedFS ignores the signed
`response-content-type` (threat model E3), so the edge must make the response safe on its own:
no MIME sniffing, a sandboxing CSP if the URL is opened as a document, no shared caching of a
signed private object, and no store headers (`Seaweed-*`, `X-Seaweedfs-*`) reaching the browser.

Two layers: the static check reads `infra/tls/Caddyfile`; the integration check runs the real
pinned Caddy image with that Caddyfile in front of a stub store that answers like SeaweedFS
(`text/html`, `Seaweed-X-Amz-Owner`, `X-Seaweedfs-Upload-Id`) and asserts what the client gets.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import ssl
import subprocess
import time
import urllib.request
import uuid

import pytest
from conftest import REPO_ROOT
from test_compose_sprint02 import CADDYFILE, media_block

CSP = "default-src 'none'; sandbox"
EXPECTED = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": CSP,
    "Cache-Control": "private, no-store",
}


def presigned_block() -> list[str]:
    block = media_block()
    start = next(i for i, ln in enumerate(block) if ln.startswith("reverse_proxy objectstore:8333"))
    end = next(i for i, ln in enumerate(block) if ln == "respond 403")
    return block[start:end]


# ---------------------------------------------------------------- static (Caddyfile)
@pytest.mark.unit
@pytest.mark.parametrize(("header", "value"), sorted(EXPECTED.items()))
def test_presigned_media_sets_safe_response_header(header: str, value: str) -> None:
    lines = presigned_block()
    wanted = f'header_down {header} "{value}"'
    assert wanted in lines, f"missing `{wanted}` in the @presigned reverse_proxy: {lines}"


@pytest.mark.unit
@pytest.mark.parametrize("prefix", ["Seaweed-", "X-Seaweedfs-"])
def test_presigned_media_strips_store_headers(prefix: str) -> None:
    assert f"header_down -{prefix}*" in presigned_block()


@pytest.mark.unit
def test_safe_headers_are_not_added_to_the_web_pages() -> None:
    # the page CSP comes from the web app (csp.ts); `sandbox` must never reach the app itself
    lines = [ln for ln in CADDYFILE.read_text().splitlines() if "sandbox" in ln and "#" not in ln]
    assert len(lines) == 1, lines


# ---------------------------------------------------------------- live (real Caddy image)
STUB_STORE = """
http://:8333 {
	header Content-Type "text/html"
	header Seaweed-X-Amz-Owner admin
	header X-Seaweedfs-Upload-Id stub-upload
	header Cache-Control "public, max-age=3600"
	respond "<script>alert(1)</script>" 200
}
"""


def _caddy_image() -> str:
    compose = (REPO_ROOT / "infra" / "compose.yaml").read_text()
    tag = re.search(r"library/caddy:([\w.\-]+)", compose)
    assert tag, "compose pins the Caddy image"
    registry = os.environ.get("DOCKERHUB_REGISTRY", "docker.io")
    return f"{registry}/library/caddy:{tag.group(1)}"


def _docker_ok() -> bool:
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def edge(tmp_path_factory: pytest.TempPathFactory):
    if not _docker_ok():
        pytest.skip("docker not available (the infra CI job runs this on ubuntu-24.04)")
    work = tmp_path_factory.mktemp("edge")
    config = CADDYFILE.read_text().replace("objectstore:8333", "127.0.0.1:8333")
    (work / "Caddyfile").write_text(config + STUB_STORE)
    port = _free_port()
    name = f"ra-edge-test-{uuid.uuid4().hex[:8]}"
    run = subprocess.run(
        [
            "docker", "run", "-d", "--rm", "--name", name,
            "-e", "S3_BUCKET_MEDIA=racket-media",
            "-p", f"127.0.0.1:{port}:443",
            "-v", f"{work / 'Caddyfile'}:/etc/caddy/Caddyfile:ro",
            _caddy_image(),
        ],
        capture_output=True, text=True,
    )  # fmt: skip
    assert run.returncode == 0, run.stderr
    try:
        yield port
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


def _get(port: int, path: str) -> tuple[int, dict[str, str]]:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # Caddy `tls internal`, throwaway container, loopback only
    req = urllib.request.Request(f"https://localhost:{port}{path}", headers={"Range": "bytes=0-9"})
    deadline = time.monotonic() + 30
    while True:
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:  # noqa: S310
                return resp.status, dict(resp.headers.items())
        except urllib.error.HTTPError as err:
            return err.code, dict(err.headers.items())
        except (urllib.error.URLError, ConnectionError, ssl.SSLError):
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


@pytest.mark.integration
def test_live_presigned_media_response_is_safe(edge: int) -> None:
    status, headers = _get(edge, "/racket-media/originals/x.mp4?X-Amz-Signature=abc")
    lower = {k.lower(): v for k, v in headers.items()}
    assert status == 200, (status, headers)
    for header, value in EXPECTED.items():
        assert lower.get(header.lower()) == value, (header, headers)
    leaked = [k for k in lower if k.startswith(("seaweed-", "x-seaweedfs-"))]
    assert leaked == [], headers


@pytest.mark.integration
def test_live_unsigned_media_is_still_refused(edge: int) -> None:
    status, _ = _get(edge, "/racket-media/originals/x.mp4")
    assert status == 403
