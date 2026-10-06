"""IT-00-10, strict form (QA-R2-02; NFR-054; AQS/SEC-06, AQS/SEC-10).

The first IT-00-10 probe counted *any* exception other than ``HTTPError`` as "BLOCKED", so a
container **with** egress passed whenever the path broke for another reason (a TLS proxy's
certificate, a timeout). This probe calls a route blocked only on a network-level failure
(no route: ``ENETUNREACH``/``EHOSTUNREACH``; no name resolution: ``gaierror``). A TLS error
means something answered, so it is OPEN; anything else is UNKNOWN, which fails the test.
A positive control runs the same probe from the ``api`` container (on the ``edge`` network)
and expects OPEN, so the test shows it can tell the two cases apart.

Needs the Compose stack. Locally without it the tests skip; in CI (CI=true) a missing stack
fails. Proposed by senior-backend-engineer for QA (test-change-requests.md, round 2);
approved by senior-qa-engineer 2026-10-05.
"""

from __future__ import annotations

import errno
import os
import shutil
import socket
import ssl
import subprocess
import urllib.error

import pytest

COMPOSE = ["docker", "compose", "-f", "../infra/compose.yaml"]
PUBLIC_IP_URL = "http://1.1.1.1/"  # plain HTTP to a literal IP: no DNS, no TLS in the way
PUBLIC_NAME_URL = "http://example.com/"
PROBE = """
import errno, socket, ssl, sys, urllib.error, urllib.request

def classify(exc):
    reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
    if isinstance(exc, urllib.error.HTTPError):
        return "OPEN http"
    if isinstance(reason, ssl.SSLError):
        return "OPEN tls"  # a peer answered the handshake
    if isinstance(reason, socket.gaierror):
        return "BLOCKED dns"
    if isinstance(reason, OSError) and reason.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH):
        return "BLOCKED " + errno.errorcode[reason.errno]
    return "UNKNOWN " + type(reason).__name__

if __name__ == "__main__":
    try:
        urllib.request.urlopen(sys.argv[1], timeout=5)
        print("OPEN response")
    except Exception as exc:
        print(classify(exc))
"""


def _classify() -> object:
    namespace: dict[str, object] = {"__name__": "probe"}
    exec(PROBE, namespace)  # noqa: S102 - our own constant, exercised as unit tests below
    return namespace["classify"]


# ---------------------------------------------------------------- the probe itself (no Docker)
TLS_FAILURE = ssl.SSLCertVerificationError("CERTIFICATE_VERIFY_FAILED")
HTTP_403 = urllib.error.HTTPError("http://x/", 403, "Forbidden", {}, None)  # type: ignore[arg-type]
REFUSED = ConnectionRefusedError(errno.ECONNREFUSED, "refused")
CASES = {
    "tls-error-is-open": (urllib.error.URLError(TLS_FAILURE), "OPEN tls"),
    "http-error-is-open": (HTTP_403, "OPEN http"),
    "timeout-is-unknown": (urllib.error.URLError(TimeoutError("t")), "UNKNOWN TimeoutError"),
    "refused-is-unknown": (urllib.error.URLError(REFUSED), "UNKNOWN ConnectionRefusedError"),
    "dns": (urllib.error.URLError(socket.gaierror(-3, "Temporary failure")), "BLOCKED dns"),
    "enetunreach": (
        urllib.error.URLError(OSError(errno.ENETUNREACH, "unreachable")),
        "BLOCKED ENETUNREACH",
    ),
    "ehostunreach": (
        urllib.error.URLError(OSError(errno.EHOSTUNREACH, "no route")),
        "BLOCKED EHOSTUNREACH",
    ),
}


@pytest.mark.parametrize(("exc", "expected"), CASES.values(), ids=CASES.keys())
def test_probe_counts_only_network_level_failures_as_blocked(
    exc: BaseException, expected: str
) -> None:
    assert _classify()(exc) == expected  # type: ignore[operator]


# ---------------------------------------------------------------- against the Compose stack
def _require_compose() -> None:
    ok = (
        shutil.which("docker") is not None
        and subprocess.run(
            [*COMPOSE, "ps", "--status", "running", "worker", "api"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.count("\n")
        >= 3  # header + worker + api
    )
    if not ok:
        if os.environ.get("CI") == "true":
            pytest.fail("Compose worker and api containers are not running in CI", pytrace=False)
        pytest.skip("needs the Compose stack (docker compose -f infra/compose.yaml up -d)")


def probe_from(service: str, url: str) -> str:
    result = subprocess.run(
        [*COMPOSE, "exec", "-T", service, "python", "-c", PROBE, url],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return result.stdout.strip() or f"NO-OUTPUT rc={result.returncode} {result.stderr[-200:]}"


def test_the_worker_has_no_route_to_a_public_ip() -> None:
    _require_compose()

    assert probe_from("worker", PUBLIC_IP_URL) in {"BLOCKED ENETUNREACH", "BLOCKED EHOSTUNREACH"}


def test_the_worker_cannot_resolve_public_names() -> None:
    _require_compose()

    assert probe_from("worker", PUBLIC_NAME_URL) == "BLOCKED dns"


def test_positive_control_the_same_probe_sees_egress_from_the_api() -> None:
    """Without this control a probe that always says BLOCKED would pass the two tests above."""
    _require_compose()

    assert probe_from("api", PUBLIC_IP_URL).startswith("OPEN")
