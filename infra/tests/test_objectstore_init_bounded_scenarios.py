"""Binds tests/features/objectstore_init_bounded.feature (CI-OBJSTORE-INIT-HANG): the one-shot's
own Compose command run under /bin/sh against a stand-in `weed` shell."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when
from test_objectstore_init_bounded import BOUND_S, BUCKET, run_init

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("objectstore_init_bounded.feature")


@pytest.fixture
def ctx(tmp_path: Path) -> dict:
    return {"dir": tmp_path}


@given("the object-store shell never answers")
def never_answers(ctx: dict) -> None:
    ctx["hang"] = 10_000


@given("the object-store shell hangs on its first call and then answers")
def hangs_once(ctx: dict) -> None:
    ctx["hang"] = 1


@when("the bucket one-shot runs")
def runs(ctx: dict) -> None:
    ctx["res"], ctx["elapsed"] = run_init(ctx["dir"], ctx["hang"])


@then("it exits non-zero within the bound and names the media bucket")
def fails_bounded(ctx: dict) -> None:
    assert ctx["res"].returncode != 0
    assert BUCKET in ctx["res"].stderr
    assert ctx["elapsed"] < BOUND_S


@then("it exits zero with the media bucket listed")
def succeeds(ctx: dict) -> None:
    assert ctx["res"].returncode == 0, ctx["res"].stdout + ctx["res"].stderr
