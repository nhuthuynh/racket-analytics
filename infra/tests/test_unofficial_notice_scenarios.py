"""Binds tests/features/unofficial_notice_plan.feature (FIX-03-2c, PD-R1S3-01-PM)."""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from unofficial_notice_fixtures import DICTIONARY, PLAN, dictionary, load, plan

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("unofficial_notice_plan.feature")


@pytest.fixture
def ctx() -> dict:
    return {}


@given(parsers.parse('a sprint plan whose rulebook line says "{words}"'))
def plan_says(ctx: dict, words: str) -> None:
    ctx["plan"] = plan(words.replace('\\"', '"'))


@given("a sprint plan with no rulebook line")
def plan_without_line(ctx: dict) -> None:
    ctx["plan"] = plan(None)


@given(parsers.parse('a metric dictionary whose rule 0.5 says "{words}"'))
def dictionary_says(ctx: dict, words: str) -> None:
    ctx["dictionary"] = dictionary(words)


@given("the shipped sprint-03 plan")
def shipped_plan(ctx: dict) -> None:
    ctx["plan"] = PLAN.read_text(encoding="utf-8")


@given("the shipped metric dictionary")
def shipped_dictionary(ctx: dict) -> None:
    ctx["dictionary"] = DICTIONARY.read_text(encoding="utf-8")


@when("the plan is checked against the decision")
def checked(ctx: dict) -> None:
    mod = load()
    try:
        ctx["problems"] = mod.check(ctx["plan"], ctx["dictionary"])
        ctx["refused"] = None
    except mod.MissingLine as exc:
        ctx["problems"] = None
        ctx["refused"] = str(exc)


@then(parsers.parse('the check fails, naming "{text}"'))
def fails_naming(ctx: dict, text: str) -> None:
    assert ctx["refused"] is None, ctx["refused"]
    assert any(text in p for p in ctx["problems"]), ctx["problems"]


@then(parsers.parse('the check is refused, naming "{text}"'))
def refused_naming(ctx: dict, text: str) -> None:
    assert ctx["refused"] is not None and text in ctx["refused"], ctx


@then("the check passes")
def passes(ctx: dict) -> None:
    assert ctx["refused"] is None, ctx["refused"]
    assert ctx["problems"] == [], ctx["problems"]
