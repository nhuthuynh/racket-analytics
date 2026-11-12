"""MVP-03 integration: `make demo` against the running Compose stack (PO MVP goal 2026-10-15).

Runs the real Makefile target, which copies the web-tls root certificate out of the stack
(ADR 0029) and seeds through the public HTTP API. Then, as the dev user the demo names, the
stats endpoint must return published metrics with samples (a fresh stack shows stats at once).

Negative case first: without a reachable stack, `make demo` stops with a pointer to `make up`
and seeds nothing. The live case needs RA_DEMO_BASE_URL (and RA_DEMO_COMPOSE when the stack is
not the default `make up` project), set by CI web-checks after its Playwright journeys.

QA-VERIFY04R5-01 (DEMO-1.1): on a stack whose four FEATURE_* flags are on (GET /config/public),
`make demo` runs twice with rc 0; Ivy's age is confirmed through the public API, so she is
admitted afterwards. The case skips on a flag-off stack.
"""

from __future__ import annotations

import os
import shlex
import subprocess

import pytest
from conftest import REPO_ROOT
from demo_live import LiveStack, live_stack, match_id_in

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


def stack_overrides(stack: LiveStack) -> list[str]:
    overrides = [f"DEMO_URL={stack.base_url}"]
    if os.environ.get("RA_DEMO_COMPOSE"):
        overrides.append(f"COMPOSE={os.environ['RA_DEMO_COMPOSE']}")
    return overrides


def test_make_demo_seeds_a_match_whose_stats_have_metrics() -> None:
    stack = live_stack()
    res = make_demo(*stack_overrides(stack))
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


def test_make_demo_twice_on_a_flag_on_stack_confirms_ivy_through_the_api() -> None:
    stack = live_stack()
    features = stack.public_features()
    if not all(features.values()):
        pytest.skip(f"needs a flag-on stack (all four FEATURE_* on); GET /config/public {features}")
    first, again = make_demo(*stack_overrides(stack)), make_demo(*stack_overrides(stack))
    assert (first.returncode, again.returncode) == (0, 0), (first.stderr[-3000:], again.stderr)
    assert "age_confirmation_required" not in first.stderr + again.stderr
    assert "already seeded" in again.stdout, again.stdout
    assert match_id_in(first.stdout) == match_id_in(again.stdout) is not None, first.stdout
    me = stack.client("ivy").request("GET", "/me")
    assert me.status == 200, (me.status, me.body[:300])
