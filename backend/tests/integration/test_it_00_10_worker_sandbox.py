"""IT-00-10 (worker sandbox, ST-009; NFR-054; AQS/SEC-06, AQS/SEC-10): from inside the worker
container a public host is unreachable while the object store is reachable.

Needs the Compose stack (infra/compose.yaml). Locally without Docker it is skipped with a
reason; in CI (CI=true) a missing stack is a failure, never a skip.
"""

from __future__ import annotations

import os

from tests.integration import test_it_00_10_worker_sandbox_strict as strict

COMPOSE = ["docker", "compose", "-f", "../infra/compose.yaml"]


# Retired 2026-10-05 (QA-R2-02, QA-R3-07): the first probe counted ANY exception other than
# HTTPError as BLOCKED, so a TLS-intercepting proxy or a timeout gave a false pass. Both tests
# now use the strict classifier: BLOCKED only on no route or no name resolution; TLS errors
# are OPEN; anything else is UNKNOWN and fails.
def _require_compose() -> None:
    # The strict check counts running containers; `ps` alone exits 0 with none running.
    strict._require_compose()


def _from_worker(url: str) -> str:
    return strict.probe_from("worker", url)


def test_public_internet_is_blocked_from_the_worker() -> None:
    """The original target (a public name over HTTPS) must fail at the network level, not at
    TLS: an intercepting proxy answering the handshake now reads OPEN tls and fails here."""
    _require_compose()

    assert _from_worker("https://example.com/") == "BLOCKED dns"


def test_object_store_is_reachable_from_the_worker() -> None:
    _require_compose()
    endpoint = os.environ.get("S3_ENDPOINT_URL_FROM_WORKER", "http://objectstore:8333/")

    assert _from_worker(endpoint).startswith("OPEN")
