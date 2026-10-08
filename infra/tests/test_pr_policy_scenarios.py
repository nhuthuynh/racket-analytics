"""Binds tests/features/pr_policy.feature (CI-POLICY-BASE; ST-003; NFR-077, NFR-078).

Each scenario builds a real git history the way GitHub presents a pull request to the
`pr-policy` job: an origin remote, the event's frozen base SHA, `main` moving afterwards, and the
runner's full-history checkout of the merge ref rebuilt on the current `main`. The steps of
`.github/workflows/ci.yml` job `pr-policy` then run verbatim, with `${{ ... }}` expressions in
their `env` filled in from that event. Unit and integration tests: test_pr_change_set.py and
test_pr_policy_merge_base.py next to this file. Bound here, not under backend/tests, because the
policy is CI tooling (SRE lane) and needs PyYAML, which the backend does not depend on.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO_ROOT as REPO
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration

scenarios("pr_policy.feature")

WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
IMMUTABILITY = "Test and gold immutability (EP/ENG-28, NFR-078)"
SIZE = "PR size (EP/ENG-04)"
E2E_SPEC = "web/e2e/sprint-01/resumable-upload.spec.ts"
UNIT_TEST = "backend/tests/unit/test_a.py"
EXPRESSION = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **GIT_ENV},
    ).stdout.strip()


def lines(n: int) -> str:
    return "".join(f"line {i}\n" for i in range(n))


def commit_and_push(repo: Path, branch: str, rel: str, text: str) -> None:
    git(repo, "checkout", "-q", branch)
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"{branch}: {rel}")
    git(repo, "push", "-q", "origin", branch)


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given("a pull request opened against main")
def pull_request(tmp_path: Path, ctx: dict[str, Any]) -> None:
    origin, dev = tmp_path / "origin.git", tmp_path / "dev"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(dev))
    git(dev, "checkout", "-q", "-b", "main")
    for rel, text in {
        E2E_SPEC: "test('resume', () => {})\n",
        UNIT_TEST: "def test_a():\n    assert 1 == 1\n",
        "docs/notes.md": "# notes\n",
    }.items():
        (dev / rel).parent.mkdir(parents=True, exist_ok=True)
        (dev / rel).write_text(text)
    git(dev, "add", "-A")
    git(dev, "commit", "-q", "-m", "base")
    git(dev, "push", "-q", "origin", "main")
    git(dev, "checkout", "-q", "-b", "pr")
    ctx.update(root=tmp_path, origin=origin, dev=dev)


def pr_changes(ctx: dict[str, Any], rel: str, text: str) -> None:
    commit_and_push(ctx["dev"], "pr", rel, text)
    # The pull_request event fires now: GitHub freezes base.sha and head.sha.
    ctx["base_sha"] = git(ctx["dev"], "rev-parse", "origin/main")
    ctx["head_sha"] = git(ctx["dev"], "rev-parse", "pr")


@given("the pull request changes only documentation")
def pr_docs_only(ctx: dict[str, Any]) -> None:
    pr_changes(ctx, "docs/notes.md", "# notes\n\nmore\n")


@given(parsers.parse("the pull request changes {n:d} lines"))
def pr_changes_lines(ctx: dict[str, Any], n: int) -> None:
    pr_changes(ctx, "backend/src/change.py", lines(n))


@given("the pull request edits an accepted unit test")
def pr_edits_unit_test(ctx: dict[str, Any]) -> None:
    pr_changes(ctx, UNIT_TEST, "def test_a():\n    pass\n")


@given("another pull request changes an accepted end-to-end test on main after the event")
def main_changes_e2e(ctx: dict[str, Any]) -> None:
    commit_and_push(ctx["dev"], "main", E2E_SPEC, "test('resume', () => { /* hold */ })\n")


@given(parsers.parse("another pull request adds {n:d} lines on main after the event"))
def main_adds_lines(ctx: dict[str, Any], n: int) -> None:
    commit_and_push(ctx["dev"], "main", "backend/src/other.py", lines(n))


@when("the PR policy checks run on the merge ref", target_fixture="results")
def run_policy(ctx: dict[str, Any]) -> dict[str, subprocess.CompletedProcess[str]]:
    runner: Path = ctx["root"] / "runner"
    runner.mkdir()
    # actions/checkout, fetch-depth 0, on the merge ref GitHub rebuilt on the current main.
    git(runner, "init", "-q")
    git(runner, "remote", "add", "origin", str(ctx["origin"]))
    git(runner, "fetch", "-q", "origin", "+refs/heads/*:refs/remotes/origin/*")
    git(runner, "checkout", "-q", "--detach", "origin/main")
    git(runner, "merge", "-q", "--no-ff", "--no-edit", ctx["head_sha"])
    (runner / "scripts").symlink_to(REPO / "scripts", target_is_directory=True)
    event = {
        "toJSON(github.event.pull_request.labels.*.name)": "[]",
        "github.event.pull_request.base.sha": ctx["base_sha"],
        "github.event.pull_request.head.sha": ctx["head_sha"],
        "github.event.pull_request.base.ref": "main",
        "github.base_ref": "main",
        "github.sha": git(runner, "rev-parse", "HEAD"),
    }

    def resolve(value: object) -> str:
        def one(m: re.Match[str]) -> str:
            assert m.group(1) in event, f"expression not modelled: {m.group(1)}"
            return event[m.group(1)]

        return EXPRESSION.sub(one, str(value))

    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"]["pr-policy"]["steps"]
    results = {}
    for step in steps:
        if "run" not in step:
            continue
        env = {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")}
        env.update(GIT_ENV)
        env.update({k: resolve(v) for k, v in (step.get("env") or {}).items()})
        results[step["name"]] = subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
            cwd=runner,
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
            check=False,
        )
    return results


@then("the test immutability check passes")
def immutability_passes(results: dict[str, subprocess.CompletedProcess[str]]) -> None:
    res = results[IMMUTABILITY]
    assert res.returncode == 0, res.stdout + res.stderr


@then("it does not name the end-to-end test changed on main")
def e2e_not_named(results: dict[str, subprocess.CompletedProcess[str]]) -> None:
    assert E2E_SPEC not in results[IMMUTABILITY].stdout


@then("the test immutability check fails naming only the edited unit test")
def immutability_fails(results: dict[str, subprocess.CompletedProcess[str]]) -> None:
    res = results[IMMUTABILITY]
    assert res.returncode == 1, res.stdout + res.stderr
    assert f"modified: {UNIT_TEST}" in res.stdout
    assert E2E_SPEC not in res.stdout


@then(parsers.parse("the PR size check passes and counts {n:d} changed lines"))
def size_passes(results: dict[str, subprocess.CompletedProcess[str]], n: int) -> None:
    res = results[SIZE]
    assert res.returncode == 0, res.stdout + res.stderr
    assert f"pr-size: {n} changed lines" in res.stdout


@then(parsers.parse("the PR size check fails and counts {n:d} changed lines"))
def size_fails(results: dict[str, subprocess.CompletedProcess[str]], n: int) -> None:
    res = results[SIZE]
    assert res.returncode == 1, res.stdout + res.stderr
    assert f"pr-size: {n} changed lines" in res.stdout
