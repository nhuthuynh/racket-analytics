"""MVP-03 integration: `make demo` against the running Compose stack (PO MVP goal 2026-10-15).

Runs the real Makefile target, which copies the web-tls root certificate out of the stack
(ADR 0029) and seeds through the public HTTP API. Then, as the dev user the demo names, the
stats endpoint must return published metrics with samples (a fresh stack shows stats at once).

Negative case first: without a reachable stack, `make demo` stops with a pointer to `make up`
and seeds nothing. The live case needs RA_DEMO_BASE_URL (and RA_DEMO_COMPOSE when the stack is
not the default `make up` project), set by CI web-checks after its Playwright journeys.
"""

from __future__ import annotations

import os
import shlex
import subprocess

import pytest
from conftest import REPO_ROOT
from demo_live import live_stack, match_id_in

pytestmark = pytest.mark.integration


def make_demo(*overrides: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "--no-print-directory", "-C", str(REPO_ROOT), "demo", *overrides],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def test_make_demo_without_a_running_stack_points_at_make_up() -> None:
    res = make_demo("COMPOSE=false", "DEMO_URL=https://localhost:9")
    assert res.returncode != 0
    assert "run 'make up' first" in res.stderr
    assert "Sign in as" not in res.stdout


def test_make_demo_seeds_a_match_whose_stats_have_metrics() -> None:
    stack = live_stack()
    overrides = [f"DEMO_URL={stack.base_url}"]
    if os.environ.get("RA_DEMO_COMPOSE"):
        overrides.append(f"COMPOSE={os.environ['RA_DEMO_COMPOSE']}")
    res = make_demo(*overrides)
    assert res.returncode == 0, (shlex.join(res.args), res.stdout[-3000:], res.stderr[-3000:])
    match_id = match_id_in(res.stdout)
    assert match_id, res.stdout

    c = stack.client("ivy")
    stats = c.request("GET", f"/matches/{match_id}/stats")
    assert stats.status == 200, stats.status
    metrics = stats.json()["metrics"]
    assert metrics, "the stats endpoint returned no metric"
    sampled = [m for m, per in metrics.items() if per["A"].get("n") or per["B"].get("n")]
    assert sampled, metrics
