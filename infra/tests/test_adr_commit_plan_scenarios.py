"""Binds tests/features/adr_commit_plan.feature (PE-R3S3-04): the plan check run as the
principal-engineer runs it, on a real git repository."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from adr_plan_repo import adr_naming, make_repo, run_check
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("adr_commit_plan.feature")


@pytest.fixture
def ctx() -> dict:
    return {}


@given("a repository whose sprint branch has three commits that are not on main")
def repo(ctx: dict, tmp_path: Path) -> None:
    ctx["repo"], ctx["shas"] = make_repo(tmp_path, 3)
    ctx["adr"] = tmp_path / "0039.md"


@given("an ADR that names only the first two commits")
def adr_two(ctx: dict) -> None:
    adr_naming(ctx["adr"], ctx["shas"][:2])


@given("an ADR that names all three commits and the first one again")
def adr_dup(ctx: dict) -> None:
    adr_naming(ctx["adr"], [*ctx["shas"], ctx["shas"][0]])


@given("an ADR that names all three commits")
def adr_all(ctx: dict) -> None:
    adr_naming(ctx["adr"], ctx["shas"])


@when(parsers.parse("the plan check runs over {rng}"))
def check(ctx: dict, rng: str) -> None:
    ctx["out"] = run_check(ctx["repo"], ctx["adr"], rng)


def _out(ctx: dict) -> subprocess.CompletedProcess[str]:
    return ctx["out"]


@then("the check fails")
def fails(ctx: dict) -> None:
    assert _out(ctx).returncode == 1, _out(ctx).stdout + _out(ctx).stderr


@then("the check fails with a usage error")
def fails_usage(ctx: dict) -> None:
    assert _out(ctx).returncode == 2, _out(ctx).stdout + _out(ctx).stderr
    assert _out(ctx).stderr.startswith("adr-plan: "), _out(ctx).stderr


@then("the check passes")
def passes(ctx: dict) -> None:
    assert _out(ctx).returncode == 0, _out(ctx).stdout + _out(ctx).stderr


@then("the report names the third commit as missing")
def names_missing(ctx: dict) -> None:
    assert f"{ctx['shas'][2][:7]}: missing (named 0 times)" in _out(ctx).stdout


@then("the report names the first commit as named 2 times")
def names_dup(ctx: dict) -> None:
    assert f"{ctx['shas'][0][:7]}: named 2 times" in _out(ctx).stdout


@then(parsers.parse("the report says {n:d} commits are each named once"))
def says_ok(ctx: dict, n: int) -> None:
    assert f"{n} commits in main..sprint, each named once" in _out(ctx).stdout
