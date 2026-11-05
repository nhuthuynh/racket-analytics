"""IT-05-08 (ST-078e; NFR-050.7; G05-07; AQS/STACK-04): every answer of the web origin carries a
Content-Security-Policy with ``frame-ancestors 'none'``, ``X-Content-Type-Options: nosniff`` and
``X-Frame-Options: DENY``: pages (found and missing), the offline page, a content-hashed app
file, the service worker (its own CSP governs the worker's fetches), the manifest and an icon.
The same-origin ``/api/*`` answers are the API's own (Next adds no header to an external rewrite):
IT-00-14 covers them; their CSP is routed in docs/sprints/05/decisions/ST-078e.md (D3).

Runs against the running web origin, ``RA_WEB_BASE_URL`` (default ``https://localhost:3000``,
the Compose web-tls proxy, ADR 0029). ``RA_WEB_CACERT`` names the dev CA's root certificate; on a
loopback origin without it, the certificate is not checked (this test reads headers, not TLS).
An unreachable origin is a failure, never a skip, so the G05-07 line cannot pass without it. CI
runs it in the E2E job, where the stack is up (RA_WEB_BASE_URL set). The one skip is CI's
integration job, which has no web server and sets no origin (reason in the report;
docs/sprints/05/decisions/ST-078e.md D2).
"""

from __future__ import annotations

import os
import re
import ssl
from urllib.parse import urlsplit

import httpx
import pytest

BASE_URL = os.environ.get("RA_WEB_BASE_URL", "https://localhost:3000").rstrip("/")
LOOPBACK = {"localhost", "127.0.0.1", "::1"}
APP_FILE = re.compile(r"""["'](/_next/static/[^"']+\.js)["']""")

# Path -> what it is. The app file is found in the home page's HTML (its name is a build hash).
FIXED_PATHS = {
    "/": "page",
    "/this-page-does-not-exist": "missing page",
    "/offline.html": "offline page",
    "/sw.js": "service worker",
    "/manifest.webmanifest": "manifest",
    "/icons/icon.svg": "icon",
}


def _verify() -> ssl.SSLContext | bool:
    cacert = os.environ.get("RA_WEB_CACERT")
    if cacert:
        return ssl.create_default_context(cafile=cacert)
    return urlsplit(BASE_URL).hostname not in LOOPBACK


@pytest.fixture(scope="module")
def web() -> httpx.Client:
    if os.environ.get("GITHUB_JOB") == "integration" and "RA_WEB_BASE_URL" not in os.environ:
        pytest.skip("IT-05-08 runs in the E2E job against the web origin (ST-078e D2)")
    client = httpx.Client(base_url=BASE_URL, verify=_verify(), timeout=30.0, follow_redirects=False)
    try:
        client.get("/")
    except httpx.HTTPError as exc:  # pragma: no cover - the failure message is the point
        pytest.fail(f"IT-05-08 needs the web origin at {BASE_URL} (set RA_WEB_BASE_URL): {exc}")
    return client


def _missing(response: httpx.Response) -> list[str]:
    headers = response.headers
    problems = []
    csp = headers.get_list("content-security-policy")
    if not csp:
        problems.append("no Content-Security-Policy")
    elif not any(re.search(r"frame-ancestors\s+'none'", policy) for policy in csp):
        problems.append(f"CSP without frame-ancestors 'none': {csp}")
    if headers.get_list("x-content-type-options") != ["nosniff"]:
        problems.append(f"X-Content-Type-Options {headers.get_list('x-content-type-options')}")
    if headers.get_list("x-frame-options") != ["DENY"]:
        problems.append(f"X-Frame-Options {headers.get_list('x-frame-options')}")
    return problems


def _paths(web: httpx.Client) -> dict[str, str]:
    home = web.get("/")
    found = APP_FILE.search(home.text)
    assert found, "positive control: the home page names a content-hashed app file"
    return {**FIXED_PATHS, found.group(1): "app file"}


def test_every_web_answer_has_csp_nosniff_and_frame_denial(web: httpx.Client) -> None:
    gaps: dict[str, list[str]] = {}
    for path, what in _paths(web).items():
        response = web.get(path)
        # Positive control: each path is really served (the missing page is a real 404 page).
        expected = 404 if what == "missing page" else 200
        assert response.status_code == expected, f"{what} {path}: {response.status_code}"
        if problems := _missing(response):
            gaps[f"{what} {path}"] = problems
    assert gaps == {}


def test_the_checker_reports_each_missing_header() -> None:
    """Negative control (testing-strategy rule 8): a bare answer fails on all three counts."""
    bare = httpx.Response(200, headers={"content-security-policy": "default-src 'self'"})
    assert _missing(bare) == [
        "CSP without frame-ancestors 'none': [\"default-src 'self'\"]",
        "X-Content-Type-Options []",
        "X-Frame-Options []",
    ]
    assert _missing(httpx.Response(200)) == [
        "no Content-Security-Policy",
        "X-Content-Type-Options []",
        "X-Frame-Options []",
    ]
