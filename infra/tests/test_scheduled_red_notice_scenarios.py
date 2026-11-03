"""Binds tests/features/scheduled_red_notice.feature (CI-NOTICE-CANCELLED; story PRC-05).

The notice scenarios run the REAL `run:` scripts of .github/workflows/scheduled-red-notice.yml
through the helpers of test_ci_scheduled_red_notice_scenarios.py (recording `gh` on PATH). The
flaky-report scenarios run ci.yml's real suite step with bash on a throwaway tree whose `uv`
stand-in prints one line and then hangs, as the pass of run 41622904539 did.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO_ROOT
from pytest_bdd import given, parsers, scenarios, then, when
from test_ci_scheduled_red_notice_scenarios import (
    OWNER,
    RUN_URL,
    ctx,  # noqa: F401  (fixture)
    event,
    gh_calls,
    run_notice,
)

pytestmark = [pytest.mark.scenario, pytest.mark.integration]
scenarios("scheduled_red_notice.feature")

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
SUITE_STEP = "Run the backend suites three times"
FAKE_UV = """#!/bin/sh
[ "$1" = sync ] && exit 0
echo "fake pass started: $*"
echo "fake last line"
exec sleep 600
"""


def flaky_job() -> dict[str, Any]:
    return yaml.safe_load(CI.read_text())["jobs"]["flaky-report"]


def suite_step() -> dict[str, Any]:
    (found,) = [s for s in flaky_job()["steps"] if s.get("name") == SUITE_STEP]
    return found


def seconds(limit: str) -> int:
    m = re.fullmatch(r"(\d+)([smh]?)", limit)
    assert m, f"not a timeout(1) duration: {limit!r}"
    return int(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600}[m.group(2)]


# ------------------------------------------------------------------ notice
@given("no notice issue is open")
def no_issue(ctx: dict[str, Any]) -> None:  # noqa: F811
    ctx["env"]["FAKE_GH_ISSUE"] = ""


@given(parsers.parse("notice issue {number:d} is open"))
def issue_open(ctx: dict[str, Any], number: int) -> None:  # noqa: F811
    ctx["env"]["FAKE_GH_ISSUE"] = str(number)


@when(parsers.parse('the scheduled "{name}" run ends with "{conclusion}"'))
def scheduled_ends(ctx: dict[str, Any], name: str, conclusion: str) -> None:  # noqa: F811
    res = run_notice(ctx, event(name, "schedule", conclusion))
    assert res.returncode == 0, res.stdout + res.stderr


@then(parsers.parse('gh opened an issue titled "{title}" assigned to the repository owner'))
def opened_issue(ctx: dict[str, Any], title: str) -> None:  # noqa: F811
    (create,) = [c for c in gh_calls(ctx) if c["args"][:2] == ["issue", "create"]]
    args = create["args"]
    assert args[args.index("--title") + 1] == title
    assert args[args.index("--assignee") + 1] == OWNER
    ctx["issue_body"] = create["body"]


@then(parsers.parse('the issue body names the conclusion "{conclusion}" and the run'))
def body_names(ctx: dict[str, Any], conclusion: str) -> None:
    assert f"`{conclusion}`" in ctx["issue_body"]
    assert RUN_URL in ctx["issue_body"]


@then(parsers.parse("gh commented on issue {number:d} naming the run"))
def commented(ctx: dict[str, Any], number: int) -> None:
    (comment,) = [c for c in gh_calls(ctx) if c["args"][:3] == ["issue", "comment", str(number)]]
    assert RUN_URL in comment["body"]


@then("gh opened no new issue")
def no_new_issue(ctx: dict[str, Any]) -> None:  # noqa: F811
    assert not [c for c in gh_calls(ctx) if c["args"][:2] == ["issue", "create"]]


@then("gh was not asked to open, comment on or close an issue")
def no_issue_writes(ctx: dict[str, Any]) -> None:  # noqa: F811
    writes = {"create", "comment", "close", "edit", "reopen"}
    assert not [c for c in gh_calls(ctx) if c["args"][0] == "issue" and c["args"][1] in writes]


# ------------------------------------------------------------------ flaky-report bound
@given("each pass of the flaky-report suites hangs")
def hanging_tree(tmp_path: Path) -> dict[str, Path]:
    tree = tmp_path / "repo"
    (tree / "backend").mkdir(parents=True)
    (tree / "infra").mkdir()
    shutil.copy(REPO_ROOT / "infra" / "env.example", tree / "infra" / "env.example")
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "uv").write_text(FAKE_UV)
    (fake / "uv").chmod(0o755)
    return {"tree": tree, "bin": fake}


@pytest.fixture
def hang() -> dict[str, Any]:
    return {}


@when(parsers.parse("the flaky-report suite step runs with a pass limit of {limit:d} seconds"))
def run_suite_step(hang: dict[str, Any], tmp_path: Path, limit: int) -> None:
    tree, fake = tmp_path / "repo", tmp_path / "bin"
    step = suite_step()
    env = {
        "PATH": f"{fake}:{os.environ['PATH']}",
        "HOME": str(tmp_path),
        **{k: str(v) for k, v in step.get("env", {}).items()},
        "PASS_TIMEOUT": f"{limit}s",
    }
    started = time.monotonic()
    hang["res"] = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step["run"]],
        cwd=tree / step["working-directory"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    hang["elapsed"] = time.monotonic() - started
    hang["reports"] = tree / "reports"


@then(parsers.parse("the step ends within {limit:d} seconds"))
def ends_within(hang: dict[str, Any], limit: int) -> None:
    res = hang["res"]
    assert res.returncode == 0, res.stdout + res.stderr
    assert hang["elapsed"] < limit, hang["elapsed"]


@then(
    parsers.parse(
        "all {n:d} passes were started, each with its output in its own log file"
    )
)
def passes_logged(hang: dict[str, Any], n: int) -> None:
    for i in range(1, n + 1):
        log = hang["reports"] / f"run-{i}.log"
        assert log.exists(), f"pass {i}: no {log.name}"
        assert "fake pass started" in log.read_text()
        assert f"pass {i}: rc=124 fake last line" in hang["res"].stdout, hang["res"].stdout
    assert "fake pass started" not in hang["res"].stdout  # only each pass's last line is logged


@then(
    parsers.parse(
        "the flaky-report suite step has its own timeout below the job's {minutes:d} minutes"
    )
)
def step_timeout(minutes: int) -> None:
    assert flaky_job()["timeout-minutes"] == minutes
    assert suite_step()["timeout-minutes"] < minutes


@then("three passes at the pass limit fit inside the step's timeout")
def passes_fit() -> None:
    step = suite_step()
    kill = re.search(r"--kill-after=(\d+[smh]?)", step["run"])
    assert kill, "each pass needs timeout --kill-after"
    per_pass = seconds(step["env"]["PASS_TIMEOUT"]) + seconds(kill.group(1))
    assert 3 * per_pass <= step["timeout-minutes"] * 60


@then("the passes' log files are uploaded with the flaky report")
def logs_uploaded() -> None:
    (upload,) = [
        s for s in flaky_job()["steps"] if s.get("uses", "").startswith("actions/upload-artifact@")
    ]
    assert upload.get("if") == "always()"
    paths = upload["with"]["path"].split()
    assert "reports/flaky.md" in paths
    assert "reports/run-*.log" in paths
