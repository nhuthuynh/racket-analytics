"""Binds tests/features/pr_check.feature (CI-FIX-PR-CHECK; ST-002).

The real scripts/pr-check.sh and the real .githooks/pre-push (installed with the real
`make hooks`) run on a throwaway checkout (pr_check_repo.py); the PR's labels come from the
local GitHub API stub over HTTP, as pr_labels.py reads them in CI.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from conftest import REPO_ROOT
from github_stub import PR_NUMBER, GitHubStub, serve
from pr_check_repo import APP, BIG, CHECKS, UNIT_TEST, Checkout, lines, status_of, summary
from pr_checkout import git
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]
scenarios("pr_check.feature")


@pytest.fixture
def world() -> dict[str, Any]:
    return {}


@pytest.fixture
def checkout(tmp_path: Path) -> Iterator[Checkout]:
    c = Checkout.create(tmp_path)
    with serve(GitHubStub()) as stub:
        c.api_url = stub.url
        c.stub = stub  # type: ignore[attr-defined]
        yield c


def _breaks(c: Checkout, what: str) -> None:
    for part in what.split(", then "):
        if part == "adds 401 lines of production code":
            c.write(BIG, lines(401))
            c.commit("feat: big tool")
        elif part == "edits an existing unit test":
            c.write(UNIT_TEST, "def test_a():\n    assert 2 == 2\n")
            c.commit("test: edit an accepted test")
        elif part == "changes production code without a red step":
            c.write(APP, "VALUE = 2\n")
            c.commit("feat: change the value")
        elif part == "adds a test and then the code it tests":
            c.write("backend/tests/unit/test_b.py", "def test_b():\n    assert True\n")
            c.commit("test: red for the value")
            c.write(APP, "VALUE = 3\n")
            c.commit("feat: the value")
        else:
            raise AssertionError(f"unknown change: {part}")


@given(parsers.parse("a ticket branch off main that {what}"))
def ticket_branch(checkout: Checkout, what: str) -> None:
    checkout.branch("s06/planted")
    _breaks(checkout, what)


@given(parsers.parse('a branch "{name}" off main that {what}'))
def named_branch(checkout: Checkout, world: dict[str, Any], name: str, what: str) -> None:
    checkout.branch(name)
    _breaks(checkout, what)
    world["branch"] = name


@given(parsers.parse('its open pull request is titled "{title}" and carries the "{label}" label'))
def open_pr(checkout: Checkout, title: str, label: str) -> None:
    checkout.pulls = [{"number": PR_NUMBER, "title": title, "head": {"ref": "s06/planted"}}]
    checkout.stub.labels = [label]  # type: ignore[attr-defined]


@given(parsers.parse('the hooks are installed with "{command}"'))
def hooks_installed(checkout: Checkout, command: str) -> None:
    assert command == "make hooks"
    res = subprocess.run(
        ["make", "-s", "-f", str(REPO_ROOT / "Makefile"), "hooks"],
        cwd=checkout.dev,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert git(checkout.dev, "config", "core.hooksPath") == ".githooks"


@when("pr-check runs on the branch")
def run_pr_check(checkout: Checkout, world: dict[str, Any]) -> None:
    world["res"] = checkout.pr_check()


@when(parsers.parse('pr-check runs on the branch with "{flag}"'))
def run_pr_check_with(checkout: Checkout, world: dict[str, Any], flag: str) -> None:
    world["res"] = checkout.pr_check(flag)


@when("the branch is pushed to origin")
def push(checkout: Checkout, world: dict[str, Any]) -> None:
    world["res"] = checkout.push(world["branch"])


@when(parsers.parse("the branch is pushed to origin {how}"))
def push_how(checkout: Checkout, world: dict[str, Any], how: str) -> None:
    flags = {"as is": [], "with --no-verify": ["--no-verify"]}[how]
    world["res"] = checkout.push(world["branch"], *flags)


def _out(world: dict[str, Any]) -> str:
    res = world["res"]
    return res.stdout + res.stderr


@then("pr-check exits non-zero")
def exits_non_zero(world: dict[str, Any]) -> None:
    assert world["res"].returncode != 0, _out(world)[-3000:]


@then("pr-check exits 0")
def exits_zero(world: dict[str, Any]) -> None:
    assert world["res"].returncode == 0, _out(world)[-5000:]


@then(parsers.parse('its summary reports {status} for "{step}"'))
def reports(world: dict[str, Any], status: str, step: str) -> None:
    assert status_of(_out(world), step) == status, summary(_out(world))


@then(parsers.parse('its summary reports SKIP for "{step}", which needs an open pull request'))
def skipped_without_pr(world: dict[str, Any], step: str) -> None:
    assert status_of(_out(world), step) == "SKIP", summary(_out(world))
    skip = next(ln for ln in summary(_out(world)) if ln.rstrip().endswith(step))
    assert "SKIP" in skip
    assert "no open pull request" in _out(world)


@then("its summary reports no FAIL")
def no_fail(world: dict[str, Any]) -> None:
    rows = summary(_out(world))
    assert len(rows) == len(CHECKS), rows
    assert not [r for r in rows if r.startswith("FAIL")], rows


@then("its summary has one line for each check, in order")
def one_line_each(world: dict[str, Any]) -> None:
    rows = summary(_out(world))
    assert len(rows) == len(CHECKS), rows
    for row, step in zip(rows, CHECKS, strict=True):
        assert row.rstrip().endswith(step), (row, step)


@then("ruff check, ruff format --check and the unit suites ran in backend")
def ran_in_backend(checkout: Checkout) -> None:
    backend = str(checkout.dev / "backend")
    calls = [c.split("\t", 1) for c in checkout.stub_calls() if not c.startswith("gh\t")]
    assert [backend, "run ruff check ."] in calls, calls
    assert [backend, "run ruff format --check ."] in calls, calls
    assert any(d == backend and a.startswith("run --quiet pytest") for d, a in calls), calls


@then("the unit suites did not run")
def unit_not_run(checkout: Checkout) -> None:
    calls = [c.split("\t", 1)[1] for c in checkout.stub_calls()]
    assert not [a for a in calls if "pytest" in a], calls


@then("the push is refused")
def push_refused(world: dict[str, Any]) -> None:
    assert world["res"].returncode != 0, _out(world)[-3000:]


@then("the push succeeds")
def push_ok(world: dict[str, Any]) -> None:
    assert world["res"].returncode == 0, _out(world)[-5000:]


@then(parsers.parse('origin has no branch "{name}"'))
def origin_lacks(checkout: Checkout, name: str) -> None:
    assert not git(checkout.origin, "branch", "--list", name)


@then(parsers.parse('origin has the branch "{name}"'))
def origin_has(checkout: Checkout, name: str) -> None:
    assert git(checkout.origin, "branch", "--list", name)


@then(parsers.parse('the push output reports {status} for "{step}"'))
def push_reports(world: dict[str, Any], status: str, step: str) -> None:
    assert status_of(_out(world), step) == status, _out(world)[-3000:]


@then("pr-check did not run")
def pr_check_not_run(checkout: Checkout, world: dict[str, Any]) -> None:
    assert "pr-check" not in _out(world), _out(world)
    assert checkout.stub_calls() == []
