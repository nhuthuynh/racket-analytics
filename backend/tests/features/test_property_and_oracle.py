"""Binds tests/features/property_and_oracle.feature, sprint-01 §14.3.7 (ST-022; NFR-002).

Written before the engine (tests first): the invariant and differential scenarios are RED until
ST-020 provides racket.sports.pickleball.rules (seams in tests/support/contract.py, ADR 0012).
The "reported usefully" scenario is a positive control on a deliberately wrong engine and is
green now.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenario, scenarios, then, when

from tests.oracle import differential, mutants
from tests.support import contract
from tests.support import scoring as sc

pytestmark = [pytest.mark.scoring]

SEED = 20261019


def _count(text: str) -> int:
    return int(text.replace(",", ""))


@scenario("property_and_oracle.feature", "A disagreement is reported usefully")
def test_a_disagreement_is_reported_usefully() -> None:
    """Positive control: green without the production engine."""


scenarios("property_and_oracle.feature")  # the remaining scenarios
for _name, _obj in list(globals().items()):
    if _name.startswith("test_") and _name != "test_a_disagreement_is_reported_usefully":
        pytest.mark.red_until(story="ST-020")(_obj)


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(parsers.parse("{count} random rally sequences"))
def random_rally_sequences(ctx: dict[str, Any], count: str) -> None:
    ctx["count"] = _count(count)


@given(parsers.parse("a game configured with target {target:d} and margin {margin:d}"))
def configured(ctx: dict[str, Any], target: int, margin: int) -> None:
    ctx["target"], ctx["margin"] = target, margin


@when("every sequence is scored")
def score_every_sequence(ctx: dict[str, Any]) -> None:
    contract.RULES_MODULE.load()
    errors: list[str] = []
    for n, seq in enumerate(sc.random_sequences(SEED + ctx["target"], ctx["count"])):
        config = sc.mechanics_config(ctx["target"], ctx["margin"], first_service=n % 2 == 0)
        try:
            states = sc.check_invariants(seq, config, "AB"[n % 2])
            sc.check_fold(seq, config, states)
        except AssertionError as exc:
            errors.append(f"sequence {n}: {exc}")
            if len(errors) >= 5:
                break
    ctx["errors"] = errors
    ctx["scored"] = n + 1


@then("no invariant from P1 to P8 is broken")
def no_invariant_broken(ctx: dict[str, Any]) -> None:
    assert ctx["errors"] == []
    assert ctx["scored"] == ctx["count"]


@when("both engines score every sequence")
def both_engines(ctx: dict[str, Any]) -> None:
    contract.RULES_MODULE.load()
    ctx["report"] = differential.compare(
        differential.production_run, sc.random_sequences(SEED, ctx["count"])
    )


@then("they agree on every sequence")
def engines_agree(ctx: dict[str, Any]) -> None:
    report = ctx["report"]
    assert report.sequences == ctx["count"]
    assert report.passed, f"{report.disagreements} disagreements; shortest: {report.shortest}"


@given("the two engines disagree on a sequence")
def engines_disagree(ctx: dict[str, Any]) -> None:
    ctx["candidate"] = mutants.receiver_scores


@when("the nightly check finishes")
def nightly_finishes(
    ctx: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "oracle.json"
    ctx["exit"] = differential.main(
        ["--sequences", "500", "--seed", str(SEED), "--json", str(out)], candidate=ctx["candidate"]
    )
    capsys.readouterr()
    ctx["report"] = json.loads(out.read_text(encoding="utf-8"))


@then("the run is marked failed")
def run_failed(ctx: dict[str, Any]) -> None:
    assert ctx["exit"] == 1
    assert ctx["report"]["passed"] is False
    assert ctx["report"]["disagreements"] > 0


@then("the report shows the shortest sequence that disagrees")
def shortest_shown(ctx: dict[str, Any]) -> None:
    shortest = ctx["report"]["shortest"]
    seq = [tuple(r) for r in shortest["sequence"]]
    rules = differential.oracle.Rules(**shortest["rules"])
    first = shortest["first_server"]
    candidate = ctx["candidate"]
    assert seq, "an empty sequence cannot show where the engines differ"
    assert candidate(seq[:-1], rules, first) == differential.oracle_run(seq[:-1], rules, first)
    assert candidate(seq, rules, first) != differential.oracle_run(seq, rules, first)
