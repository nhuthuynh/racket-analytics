"""Binds tests/features/metric_dictionary.feature (ST-043; FR-102; NFR-075).

Domain binding: the steps drive ``MetricDictionary.published()`` and
``version_bump_violations()`` on copies of the shipped dictionary and its lock; no I/O beyond
reading the two package files. "The locked metric dictionary on main" is the shipped pair taken
as the previous lock (what the integration test reads from the merge base with ``git show``).
"""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from racket.sports.pickleball.metrics import (
    LOCK_PATH,
    METRICS_PATH,
    DefinitionLock,
    MetricDictionary,
    definition_digest,
    version_bump_violations,
)

scenarios("metric_dictionary.feature")


def _shipped() -> tuple[dict[str, Any], dict[str, Any]]:
    data = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    return copy.deepcopy(data), copy.deepcopy(lock)


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(parsers.parse('the metric dictionary has "{entry_id}" as "{status}"'))
def dictionary_with_status(ctx: dict[str, Any], entry_id: str, status: str) -> None:
    data, _ = _shipped()
    (entry,) = [e for e in data["entries"] if e["id"] == entry_id]
    entry["status"] = status
    ctx["dictionary"] = MetricDictionary.parse(data)


@when("the published metrics are listed")
def list_published(ctx: dict[str, Any]) -> None:
    ctx["published"] = [e.id for e in ctx["dictionary"].published()]


@then(parsers.parse('"{entry_id}" is not among them'))
def not_published(ctx: dict[str, Any], entry_id: str) -> None:
    assert entry_id not in ctx["published"]
    assert ctx["dictionary"].is_published(entry_id) is False


@then(parsers.parse('"{entry_id}" is among them'))
def published(ctx: dict[str, Any], entry_id: str) -> None:
    assert entry_id in ctx["published"]
    assert ctx["dictionary"].is_published(entry_id) is True


@given("the locked metric dictionary on main")
def locked_on_main(ctx: dict[str, Any]) -> None:
    data, lock = _shipped()
    ctx["data"], ctx["lock"] = data, lock
    ctx["previous"] = DefinitionLock.parse(copy.deepcopy(lock))
    assert version_bump_violations(MetricDictionary.parse(data), ctx["previous"]) == ()


def _change_formula(ctx: dict[str, Any], entry_id: str) -> dict[str, Any]:
    (entry,) = [e for e in ctx["data"]["entries"] if e["id"] == entry_id]
    entry["formula"] = entry["formula"] + " (excluding lets)"
    return entry


@when(
    parsers.parse('the formula of "{entry_id}" changes and its locked digest is rewritten in place')
)
def rewrite_in_place(ctx: dict[str, Any], entry_id: str) -> None:
    _change_formula(ctx, entry_id)
    changed = MetricDictionary.parse(ctx["data"]).entry(entry_id)
    # the PE-ST043-01 bypass: the digest of the existing version is overwritten, no bump
    ctx["lock"]["entries"][entry_id]["0.1"] = definition_digest(changed)


@when(parsers.parse('the formula of "{entry_id}" changes with a version bump recorded in the lock'))
def change_with_bump(ctx: dict[str, Any], entry_id: str) -> None:
    entry = _change_formula(ctx, entry_id)
    entry["version"] = "0.2"
    ctx["data"]["version"] = "0.2"
    changed = MetricDictionary.parse(ctx["data"]).entry(entry_id)
    ctx["lock"]["version"] = "0.2"
    ctx["lock"]["entries"][entry_id]["0.2"] = definition_digest(changed)


def _violations(ctx: dict[str, Any]) -> tuple[str, ...]:
    return version_bump_violations(
        MetricDictionary.parse(ctx["data"]),
        DefinitionLock.parse(ctx["lock"]),
        previous=ctx["previous"],
    )


@then(parsers.parse('the version check fails and names "{entry_id}"'))
def check_fails(ctx: dict[str, Any], entry_id: str) -> None:
    violations = _violations(ctx)
    assert violations, "a silent definition change passed the version check"
    assert any(v.startswith(entry_id) for v in violations), violations


@then("the version check passes")
def check_passes(ctx: dict[str, Any]) -> None:
    assert _violations(ctx) == ()
