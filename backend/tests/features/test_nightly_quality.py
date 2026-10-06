"""Binds tests/features/nightly_quality.feature (ST-024; sprint-01 §14.3.8; NFR-041, NFR-042).

The workflow file itself is checked by infra/tests (SRE lane). Here: the published nightly
result in docs/sprints/01/status.json and the SLI arithmetic (seams in tests/support/contract.py).
"Nightly run completes" is RED until ST-024; the SLI scenarios are in the gate.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenario, scenarios, then, when

from tests.support import contract
from tests.support.paths import REPO


# Only the scenario that needs the nightly job itself waits on ST-024 (QA-RV1-06 / SRE-S2-04);
# the SLI arithmetic scenarios pass today and belong in the per-PR gate.
@pytest.mark.red_until(story="ST-024")
@scenario("nightly_quality.feature", "Nightly run completes")
def test_nightly_run_completes() -> None:
    pass


scenarios("nightly_quality.feature")

LIFECYCLES = {
    "reached full length": ("created", "completed"),
    "was resumed by a live client and finished": ("created", "completed"),
    "was abandoned by the user": ("created", "cancelled"),
}


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given("the nightly quality run has finished")
def nightly_finished() -> None:
    """The nightly job (ST-024) writes its result into the sprint status file."""


@when("the team opens the sprint status file")
def open_status(ctx: dict[str, Any]) -> None:
    status = json.loads((REPO / "docs" / "sprints" / "01" / "status.json").read_text("utf-8"))
    ctx["nightly"] = status.get(contract.STATUS_NIGHTLY_KEY)


@then("it shows the oracle result and the mutation score with the run date")
def shows_results(ctx: dict[str, Any]) -> None:
    nightly = ctx["nightly"]
    assert nightly, "no nightly result in docs/sprints/01/status.json"
    dt.date.fromisoformat(nightly["run_date"])
    assert nightly["oracle"]["sequences"] >= 100_000
    assert isinstance(nightly["oracle"]["disagreements"], int)
    assert 0.0 <= float(nightly["mutation"]["score"]) <= 1.0


@given(parsers.parse("an upload that {outcome}"))
def an_upload(ctx: dict[str, Any], outcome: str) -> None:
    ctx["events"] = [LIFECYCLES[outcome]]


@when("the upload completion indicator is read")
def read_completion(ctx: dict[str, Any]) -> None:
    ctx["sli"] = contract.SLI_UPLOAD_COMPLETION.load()(ctx["events"])


@then(parsers.parse("that upload is counted as {counted}"))
def counted_as(ctx: dict[str, Any], counted: str) -> None:
    good, base = ctx["sli"]
    expected = {"completed": (1, 1), "not in the base": (0, 0)}[counted]
    assert (good, base) == expected


@given(parsers.parse("{total:d} requests of which {limited:d} were rate limited and none failed"))
def requests(ctx: dict[str, Any], total: int, limited: int) -> None:
    ctx["codes"] = [429] * limited + [200] * (total - limited)


@when("the availability indicator is read")
def read_availability(ctx: dict[str, Any]) -> None:
    ctx["availability"] = contract.SLI_AVAILABILITY.load()(ctx["codes"])


@then(parsers.parse("availability is {pct:d}%"))
def availability_is(ctx: dict[str, Any], pct: int) -> None:
    assert ctx["availability"] == pytest.approx(pct / 100)
