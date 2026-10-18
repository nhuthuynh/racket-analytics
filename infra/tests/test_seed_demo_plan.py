"""IT-04-11 (ST-064): `make demo` creates one plan for Ivy; running it again keeps it.

The real scripts/demo/seed_demo.py over HTTP. Always against the loopback fake of the public API
(demo_fake_api.py); also against the live Compose stack named by RA_DEMO_BASE_URL (and
RA_DEMO_CACERT), skipped without it, as the MVP-03 live scenarios are. Negative cases first.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from demo_fake_api import FakeApi, fake_api
from demo_live import live_stack, run_demo
from test_seed_demo_plan_scenarios import DEMO_PREFERENCES, plan_id_in

pytestmark = pytest.mark.integration


@pytest.fixture
def fake() -> Iterator[FakeApi]:
    with fake_api() as f:
        yield f


def _demo(fake: FakeApi, tmp_path: Path):  # noqa: ANN202
    env = tmp_path / "env"
    env.write_text("APP_ENV=dev\n")
    return run_demo("--base-url", fake.url, "--env-file", str(env), timeout=60)


def _paths(fake: FakeApi) -> list[str]:
    return [f"{method} {path}" for method, path, _ in fake.requests]


def test_a_stack_without_the_plan_api_fails_reading_the_plan_and_generates_none(
    fake: FakeApi, tmp_path: Path
) -> None:
    fake.plan_api = False
    res = _demo(fake, tmp_path)
    assert res.returncode == 1, (res.stdout, res.stderr)
    assert "make demo failed: read the plan:" in res.stderr, res.stderr
    assert fake.plan_posts() == [], _paths(fake)


def test_a_refused_generation_is_rc_1_and_prints_no_plan_page(
    fake: FakeApi, tmp_path: Path
) -> None:
    fake.refuse_plan = "no_tagged_match"
    res = _demo(fake, tmp_path)
    assert res.returncode == 1, (res.stdout, res.stderr)
    assert "generate the plan: HTTP 409" in res.stderr, res.stderr
    assert "no_tagged_match" in res.stderr
    assert "/plan" not in res.stdout


def test_an_existing_plan_is_kept_and_no_plan_is_generated(fake: FakeApi, tmp_path: Path) -> None:
    fake.plans.append({"id": "plan-kept", "preferences": {"players_available": 4}})
    res = _demo(fake, tmp_path)
    assert res.returncode == 0, (res.stdout, res.stderr)
    assert fake.plan_posts() == [], _paths(fake)
    assert plan_id_in(res.stdout) == "plan-kept", res.stdout
    assert "already generated" in res.stdout


def test_the_plan_is_generated_once_after_the_match_and_its_stats(
    fake: FakeApi, tmp_path: Path
) -> None:
    first, again = _demo(fake, tmp_path), _demo(fake, tmp_path)
    assert (first.returncode, again.returncode) == (0, 0), (first.stderr, again.stderr)
    assert fake.plan_posts() == [DEMO_PREFERENCES], _paths(fake)
    paths = _paths(fake)
    stats = paths.index("GET /api/matches/m-demo-1/stats")
    assert paths.index("POST /api/me/plan") > stats, paths
    assert plan_id_in(first.stdout) == plan_id_in(again.stdout) == "plan-1"
    assert f"Open {fake.url}/plan" in first.stdout
    # the match lines are unchanged: the stats link is still printed before the plan
    assert first.stdout.index("/stats") < first.stdout.index("/plan"), first.stdout


def test_live_stack_one_plan_and_a_rerun_keeps_its_id() -> None:
    stack = live_stack()
    first, again = run_demo(*stack.demo_args()), run_demo(*stack.demo_args())
    assert (first.returncode, again.returncode) == (0, 0), (first.stderr[-2000:], again.stderr)
    plan_id = plan_id_in(first.stdout)
    assert plan_id, first.stdout
    assert plan_id_in(again.stdout) == plan_id, again.stdout
    assert f"Open {stack.base_url}/plan" in first.stdout
    r = stack.client().request("GET", "/me/plan")
    assert r.status == 200, r.status
    body = r.json()
    assert body["id"] == plan_id
    assert body["sessions"], "the demo plan has no session"
    for s in body["sessions"]:
        for a in s["assignments"]:
            c = a["citation"]
            assert {"metric_id", "value", "n", "rally_ids"} <= set(c), a
