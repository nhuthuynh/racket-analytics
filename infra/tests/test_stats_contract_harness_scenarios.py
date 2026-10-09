"""Binds tests/features/stats_contract_harness.feature (PE-DESIGN-3; ADR 0033 rule 2).

The harness modules are the real `scripts/measure` files; the contract is the real
`docs/architecture/api-sprint-03.md`, read by the parsers of `test_statscontract_doc.py`.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from test_statscontract_doc import CONTRACT, _load, label_routes, section

pytestmark = pytest.mark.unit
scenarios("stats_contract_harness.feature")


@pytest.fixture
def world() -> dict[str, Any]:
    return {}


@given("the harness built from the contract")
def harness(world: dict[str, Any]) -> None:
    world["sk"] = _load("statscontract")
    world["live"] = _load("live_stats")
    world["doc"] = CONTRACT.read_text(encoding="utf-8")


@when(
    parsers.parse("DELETE /me answers {status:d} and signing in again gives a new, empty account")
)
def delete_me(world: dict[str, Any], status: int) -> None:
    world["step"] = world["live"].judge_account_deletion(
        deleted_id="acc-deleted",
        status=status,
        old_session=401,
        back=True,
        items=[],
        again_me={"id": "acc-new"},
    )


@then(parsers.parse('the account deletion step fails, naming "{text}"'))
def step_fails(world: dict[str, Any], text: str) -> None:
    assert world["step"]["ok"] is False, world["step"]
    assert world["step"]["problems"] == [text]


@then("the account deletion step passes")
def step_passes(world: dict[str, Any]) -> None:
    assert world["step"]["ok"] is True, world["step"]
    assert world["step"]["problems"] == []


@then("the harness purge command and service are the ones api-sprint-03 §4.4 names")
def purge_named(world: dict[str, Any]) -> None:
    body = section(world["doc"], "4.4 Purge job contract")
    sk = world["sk"]
    assert f"`$DC exec -T {sk.PURGE_SERVICE} {sk.PURGE_ONCE}`" in body


@then("the harness label routes are exactly the ones api-sprint-03 §5.2 lists")
def label_named(world: dict[str, Any]) -> None:
    assert set(world["sk"].LABEL_ROUTES.values()) == label_routes(world["doc"])
