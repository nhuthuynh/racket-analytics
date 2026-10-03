"""IT-00-10 (worker sandbox, ST-009; NFR-054; AQS/SEC-06, AQS/SEC-10): from inside the worker
container a public host is unreachable while the object store is reachable.

Needs the Compose stack (infra/compose.yaml). Locally without Docker it is skipped with a
reason; in CI (CI=true) a missing stack is a failure, never a skip.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.red_until(story="ST-009")

COMPOSE = ["docker", "compose", "-f", "../infra/compose.yaml"]
# An HTTP error status still proves the network path is open (e.g. S3 answers 403 or 404).
PROBE = (
    "import sys,urllib.error,urllib.request\n"
    "try:\n"
    "    urllib.request.urlopen(sys.argv[1], timeout=5); print('OPEN')\n"
    "except urllib.error.HTTPError:\n"
    "    print('OPEN')\n"
    "except Exception as e:\n"
    "    print('BLOCKED', type(e).__name__)\n"
)


def _require_compose() -> None:
    ok = (
        shutil.which("docker") is not None
        and subprocess.run(
            [*COMPOSE, "ps", "--status", "running", "worker"], capture_output=True, check=False
        ).returncode
        == 0
    )
    if not ok:
        if os.environ.get("CI") == "true":
            pytest.fail("Compose worker container is not running in CI", pytrace=False)
        pytest.skip("needs the Compose stack (docker compose -f infra/compose.yaml up -d)")


def _from_worker(url: str) -> str:
    result = subprocess.run(
        [*COMPOSE, "exec", "-T", "worker", "python", "-c", PROBE, url],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return result.stdout.strip()


def test_public_internet_is_blocked_from_the_worker() -> None:
    _require_compose()

    assert _from_worker("https://example.com/").startswith("BLOCKED")


def test_object_store_is_reachable_from_the_worker() -> None:
    _require_compose()
    endpoint = os.environ.get("S3_ENDPOINT_URL_FROM_WORKER", "http://objectstore:8333/")

    assert _from_worker(endpoint) == "OPEN"
