"""Binds tests/features/ci_e2e_bounded.feature (CI-E2E-JOURNEYS-TIMEOUT; NFR-073, NFR-074):
the real ci.yml's E2E job, read as data."""

from __future__ import annotations

import re
from typing import Any

import pytest
import yaml
from conftest import REPO_ROOT
from pytest_bdd import given, parsers, scenarios, then

pytestmark = pytest.mark.unit
scenarios("ci_e2e_bounded.feature")

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
SPECS = REPO_ROOT / "web" / "e2e"
LEG = r"\$\{\{\s*matrix\.project\s*\}\}"
GATED = '--grep-invert "@red-until-"'
LISTED = '--grep "@red-until-"'


def _job() -> dict[str, Any]:
    return yaml.safe_load(CI.read_text())["jobs"]["e2e"]


def _step(job: dict[str, Any], needle: str) -> dict[str, Any]:
    found = [s for s in job["steps"] if needle in s.get("run", "")]
    assert len(found) == 1, [s.get("name") for s in found]
    return found[0]


def _index(job: dict[str, Any], step: dict[str, Any]) -> int:
    return next(i for i, s in enumerate(job["steps"]) if s is step)


def _option(run: str, name: str) -> str | None:
    found = re.search(rf"--{name}[= ]\"?([^\s\"]+)\"?", run)
    return found.group(1) if found else None


def red_until_tests() -> int:
    """``@red-until-`` tags in the spec files: one per red-first test (ADR 0046)."""
    return sum(p.read_text().count("@red-until-") for p in sorted(SPECS.rglob("*.spec.ts")))


@given("the CI workflow", target_fixture="job")
def job() -> dict[str, Any]:
    return _job()


# ---------------------------------------------------------------- legs
@then("the E2E job runs one leg per browser project: chromium and webkit")
def legs(job: dict[str, Any]) -> None:
    matrix = job.get("strategy", {}).get("matrix", {})
    assert matrix.get("project") == ["chromium", "webkit"], job.get("strategy")
    assert re.search(LEG, job["name"]), job["name"]


@then("a failing leg does not cancel the other leg")
def no_fail_fast(job: dict[str, Any]) -> None:
    assert job["strategy"].get("fail-fast") is False, job["strategy"]


@then("both Playwright steps of a leg run only that leg's browser project")
def one_project(job: dict[str, Any]) -> None:
    for needle in (GATED, LISTED):
        run = _step(job, needle)["run"]
        assert re.search(rf"--project[= ]\"?{LEG}\"?", run), run


@then("each leg keeps its Playwright report under its own name")
def own_report(job: dict[str, Any]) -> None:
    uploads = [s for s in job["steps"] if "upload-artifact" in s.get("uses", "")]
    report = next(s for s in uploads if s["with"]["path"] == "web/playwright-report/")
    assert re.fullmatch(rf"playwright-report-{LEG}", report["with"]["name"]), report["with"]
    assert report.get("if") == "always()", report


# ---------------------------------------------------------------- the bound
@then(parsers.parse("the gated Playwright step stops the run after at most {limit:d} minutes"))
def global_timeout(job: dict[str, Any], limit: int) -> None:
    run = _step(job, GATED)["run"]
    value = _option(run, "global-timeout")
    assert value is not None and value.isdigit(), run
    assert 0 < int(value) <= limit * 60_000, value
    # The bound must leave room for the listed step and the report inside the job limit.
    assert int(value) <= (job["timeout-minutes"] - 15) * 60_000, (value, job["timeout-minutes"])


@then("the gated step prints each test with its duration as it ends")
def list_reporter(job: dict[str, Any]) -> None:
    run = _step(job, GATED)["run"]
    reporters = (_option(run, "reporter") or "").split(",")
    assert "list" in reporters, run
    assert "html" in reporters, run  # the report the artifact keeps


@then("the listed red-until step runs each of its leg's tests at once")
def listed_workers(job: dict[str, Any]) -> None:
    run = _step(job, LISTED)["run"]
    workers = _option(run, "workers")
    assert workers is not None and workers.isdigit(), run
    assert int(workers) >= red_until_tests(), (workers, red_until_tests())


# ---------------------------------------------------------------- what explains a slow run
@then("the E2E job prints the runner's CPU model, CPU count and memory before the journeys")
def runner_facts(job: dict[str, Any]) -> None:
    facts = [s for s in job["steps"] if "/proc/cpuinfo" in s.get("run", "")]
    assert len(facts) == 1, [s.get("name") for s in job["steps"]]
    run = facts[0]["run"]
    for needle in ("model name", "nproc", "free -m"):
        assert needle in run, run
    assert _index(job, facts[0]) < _index(job, _step(job, GATED))


@then("the E2E job prints the service logs when it fails or is cancelled")
def service_logs(job: dict[str, Any]) -> None:
    logs = next(s for s in job["steps"] if s.get("name", "").startswith("Service logs"))
    assert logs["if"].replace(" ", "") == "failure()||cancelled()", logs
    assert "logs --no-color" in logs["run"], logs


# ---------------------------------------------------------------- unit edge cases
def test_each_leg_keeps_the_single_ci_worker_of_the_gated_step() -> None:
    """The legs split the browsers, never the workers of one stack (single CI worker kept)."""
    run = _step(_job(), GATED)["run"]
    assert _option(run, "workers") is None, run


def test_the_listed_step_selects_the_same_leg_as_the_gated_step() -> None:
    job = _job()
    gated, listed = _step(job, GATED)["run"], _step(job, LISTED)["run"]
    assert _option(gated, "project") is not None, gated
    assert _option(gated, "project") == _option(listed, "project"), (gated, listed)


def test_the_browser_install_follows_the_leg() -> None:
    job = _job()
    install = _step(job, "playwright install")["run"]
    assert re.search(rf"playwright install --with-deps \"?{LEG}\"?", install), install


def test_the_red_until_count_finds_the_tags_in_the_specs() -> None:
    assert red_until_tests() >= 1  # the listed-step check above is not vacuous


def test_the_infra_tests_job_installs_web_before_the_real_playwright_run() -> None:
    """ci_e2e_stall_report.feature runs web/'s Playwright in the infra-tests job: it must find
    it installed, so the scenario fails instead of skipping when it is missing."""
    steps = yaml.safe_load(CI.read_text())["jobs"]["infra-tests"]["steps"]
    node = next(i for i, s in enumerate(steps) if "setup-node" in s.get("uses", ""))
    install = next(
        i
        for i, s in enumerate(steps)
        if "pnpm install --frozen-lockfile" in s.get("run", "")
        and s.get("working-directory") == "web"
    )
    tests = next(i for i, s in enumerate(steps) if "pytest" in s.get("run", ""))
    assert node < install < tests
