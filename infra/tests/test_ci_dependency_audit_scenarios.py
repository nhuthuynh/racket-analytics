"""Binds tests/features/ci_dependency_audit.feature (CI-DAILY-AUDIT; ST-002; NFR-062).

PO decision 2026-10-28.

scripts/ci/security_upgrade.py runs as a subprocess exactly as the workflow runs it, over
pip-audit JSON reports, with a recording stand-in for `uv` that rewrites the project's real
uv.lock. The workflow scenarios read the real .github/workflows/dependency-audit.yml.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]
scenarios("ci_dependency_audit.feature")

SCRIPT = SCRIPTS_DIR / "ci" / "security_upgrade.py"
WF = REPO_ROOT / ".github" / "workflows"
POLICY_LABELS = ("size-waiver", "qa-approved-test-change")

# A recording `uv`: logs its argv, and moves each --upgrade-package to the version the
# FAKE_UV_TO map names, in ./uv.lock, the way `uv lock --upgrade-package` would.
FAKE_UV = r"""
import json, os, re, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ["FAKE_UV_LOG"], "a") as log:
    log.write(json.dumps({"cwd": os.getcwd(), "args": args}) + "\n")
to = json.loads(os.environ.get("FAKE_UV_TO", "{}"))
lock = Path("uv.lock")
text = lock.read_text()
for i, a in enumerate(args):
    if a == "--upgrade-package":
        pkg = args[i + 1]
        text = re.sub(
            r'(name = "%s"\nversion = ")[^"]+(")' % re.escape(pkg),
            lambda m: m.group(1) + to[pkg] + m.group(2),
            text,
        )
lock.write_text(text)
"""


def lock_text(packages: dict[str, str]) -> str:
    rows = ["version = 1", "revision = 3", 'requires-python = ">=3.11"', ""]
    for name, version in packages.items():
        rows += [
            "[[package]]",
            f'name = "{name}"',
            f'version = "{version}"',
            'source = { registry = "https://pypi.org/simple" }',
            "",
        ]
    return "\n".join(rows)


def audit_report(deps: list[dict[str, Any]]) -> str:
    return json.dumps({"dependencies": deps, "fixes": []})


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    root = tmp_path / "repo"
    (root / "backend").mkdir(parents=True)
    fake = tmp_path / "fake_uv.py"
    fake.write_text(FAKE_UV)
    return {
        "root": root,
        "out": tmp_path / "out",
        "uv_log": tmp_path / "uv.log",
        "uv": f"{sys.executable} {fake}",
        "reports": tmp_path / "reports",
        "fix_to": {},
    }


@given(parsers.parse('the backend lock lists "{pkg}" at "{version}"'))
def backend_lock(ctx: dict[str, Any], pkg: str, version: str) -> None:
    (ctx["root"] / "backend" / "uv.lock").write_text(lock_text({pkg: version, "idna": "3.10"}))


def write_backend_report(ctx: dict[str, Any], deps: list[dict[str, Any]]) -> None:
    ctx["reports"].mkdir(exist_ok=True)
    (ctx["reports"] / "backend.json").write_text(audit_report(deps))


@given(parsers.parse('pip-audit reports "{advisory}" against "{pkg}" "{version}" fixed in "{fix}"'))
def vulnerable_with_fix(
    ctx: dict[str, Any], advisory: str, pkg: str, version: str, fix: str
) -> None:
    ctx["fix_to"][pkg] = fix
    vuln = {"id": advisory, "fix_versions": [fix], "aliases": [], "description": "x"}
    write_backend_report(
        ctx,
        [
            {"name": pkg, "version": version, "vulns": [vuln]},
            {"name": "idna", "version": "3.10", "vulns": []},
        ],
    )


@given(
    parsers.parse('pip-audit reports "{advisory}" against "{pkg}" "{version}" with no fix version')
)
def vulnerable_without_fix(ctx: dict[str, Any], advisory: str, pkg: str, version: str) -> None:
    vuln = {
        "id": advisory,
        "fix_versions": [],
        "aliases": ["GHSA-aaaa-bbbb-cccc"],
        "description": "x",
    }
    write_backend_report(ctx, [{"name": pkg, "version": version, "vulns": [vuln]}])


@given("pip-audit reports no vulnerability")
def clean(ctx: dict[str, Any]) -> None:
    write_backend_report(ctx, [{"name": "certifi", "version": "2026.10.19", "vulns": []}])


def run(
    ctx: dict[str, Any], date: str, with_backend_report: bool = True
) -> subprocess.CompletedProcess[str]:
    audits = ["--audit", f"backend={ctx['reports'] / 'backend.json'}"]
    if not with_backend_report:
        audits = ["--audit", f"backend={ctx['reports'] / 'missing.json'}"]
    env = {
        "PATH": "/usr/bin:/bin",
        "FAKE_UV_LOG": str(ctx["uv_log"]),
        "FAKE_UV_TO": json.dumps(ctx["fix_to"]),
    }
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(ctx["root"]),
            *audits,
            "--date",
            date,
            "--uv",
            ctx["uv"],
            "--out-dir",
            str(ctx["out"]),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=60,
    )


@when(parsers.parse('the security upgrade runs on "{date}"'), target_fixture="result")
def runs(ctx: dict[str, Any], date: str) -> subprocess.CompletedProcess[str]:
    res = run(ctx, date)
    assert res.returncode == 0, res.stdout + res.stderr
    return res


@when("the security upgrade runs without the backend audit report", target_fixture="result")
def runs_without_report(ctx: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    return run(ctx, "2026-10-28", with_backend_report=False)


def uv_calls(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    if not ctx["uv_log"].exists():
        return []
    return [json.loads(line) for line in ctx["uv_log"].read_text().splitlines()]


@then(parsers.parse('uv upgrades only "{pkg}" in the backend project'))
def upgraded_only(ctx: dict[str, Any], pkg: str) -> None:
    calls = uv_calls(ctx)
    assert [c["args"] for c in calls] == [["lock", "--upgrade-package", pkg]], calls
    assert Path(calls[0]["cwd"]) == ctx["root"] / "backend"
    assert f'version = "{ctx["fix_to"][pkg]}"' in (ctx["root"] / "backend" / "uv.lock").read_text()


@then("uv is not run")
def uv_not_run(ctx: dict[str, Any]) -> None:
    assert uv_calls(ctx) == []


@then(parsers.parse('the pull request title is "{title}"'))
def pr_title(ctx: dict[str, Any], title: str) -> None:
    assert (ctx["out"] / "pr-title.txt").read_text().strip() == title


@then(parsers.parse('the pull request body lists "{advisory}" with "{old}" and "{new}"'))
def pr_body(ctx: dict[str, Any], advisory: str, old: str, new: str) -> None:
    body = (ctx["out"] / "pr-body.md").read_text()
    row = next(line for line in body.splitlines() if advisory in line)
    assert old in row, row
    assert new in row, row


@then("no pull request is written")
def no_pr(ctx: dict[str, Any]) -> None:
    assert not (ctx["out"] / "pr-body.md").exists()


@then("no issue is written")
def no_issue(ctx: dict[str, Any]) -> None:
    assert not (ctx["out"] / "issue-body.md").exists()


@then(parsers.parse('the issue body lists "{advisory}" for "{pkg}"'))
def issue_lists(ctx: dict[str, Any], advisory: str, pkg: str) -> None:
    body = (ctx["out"] / "issue-body.md").read_text()
    row = next(line for line in body.splitlines() if advisory in line)
    assert pkg in row, row


@then(parsers.parse('the job fails naming "{project}"'))
def fails_naming(result: subprocess.CompletedProcess[str], project: str) -> None:
    assert result.returncode != 0
    assert project in result.stdout + result.stderr


# ------------------------------------------------------------------ workflow
def workflow() -> dict[str, Any]:
    return yaml.safe_load((WF / "dependency-audit.yml").read_text())


def job() -> dict[str, Any]:
    jobs = workflow()["jobs"]
    assert len(jobs) == 1, list(jobs)
    return next(iter(jobs.values()))


def run_scripts() -> str:
    return "\n".join(step.get("run", "") for step in job()["steps"])


@then("the dependency audit workflow runs on a daily schedule and on manual dispatch")
def daily(ctx: dict[str, Any]) -> None:
    on = workflow()[True]  # PyYAML reads `on:` as True
    assert set(on) == {"schedule", "workflow_dispatch"}
    (cron,) = [entry["cron"] for entry in on["schedule"]]
    minute, hour, dom, month, dow = cron.split()
    assert (dom, month, dow) == ("*", "*", "*"), cron
    assert minute.isdigit(), cron
    assert hour.isdigit(), cron


@then("the dependency audit job may only write contents, pull requests and issues")
def least_privilege(ctx: dict[str, Any]) -> None:
    assert workflow()["permissions"] == {}
    assert job()["permissions"] == {
        "contents": "write",
        "pull-requests": "write",
        "issues": "write",
    }


TOKEN_STEPS = {  # the only steps that may see GH_TOKEN (review PE-1, PR #150)
    "Start from the upgrade branch merged with main (or from main)",
    "Commit and push the upgrade branch",
    "Open or update the draft upgrade pull request",
    "Open or update the advisory issue",
}
ADMIN_SETTING = "Allow GitHub Actions to create and approve pull requests"


@then("the dependency audit checks out without persisting the token")
def no_persisted_token(ctx: dict[str, Any]) -> None:
    checkouts = [s for s in job()["steps"] if s.get("uses", "").startswith("actions/checkout@")]
    assert checkouts and all(s["with"]["persist-credentials"] is False for s in checkouts)


@then("only the steps that fetch, push or call GitHub get the token")
def token_only_where_needed(ctx: dict[str, Any]) -> None:
    assert "GH_TOKEN" not in job().get("env", {})
    with_token = {s["name"] for s in job()["steps"] if "GH_TOKEN" in s.get("env", {})}
    assert with_token == TOKEN_STEPS
    for step in job()["steps"]:  # uv, pip-audit, pnpm and corepack run untrusted package code
        if re.search(r"(^|\s)(uv|pip-audit|pnpm|corepack|python3) ", step.get("run", ""), re.M):
            assert "GH_TOKEN" not in step.get("env", {}), step["name"]


@then("the commit and the push run no git hook")
def no_git_hook(ctx: dict[str, Any]) -> None:
    step = next(s for s in job()["steps"] if s.get("name") == "Commit and push the upgrade branch")
    assert "GIT_CONFIG_KEY_1=core.hooksPath GIT_CONFIG_VALUE_1=/dev/null" in step["run"]
    for verb in ("commit", "push"):
        assert re.search(rf"^\s*git {verb} --no-verify ", step["run"], re.M), verb


@then(parsers.parse('ci-cd.md lists "{setting}" for a human admin'))
def admin_setting_documented(ctx: dict[str, Any], setting: str) -> None:
    text = (REPO_ROOT / "docs" / "process" / "ci-cd.md").read_text()
    section = text.split("### 2.1 Repository settings a human admin must apply")[1].split("\n## ")[0]
    assert setting in section


@then("a failed pull request creation names that setting")
def create_failure_names_setting(ctx: dict[str, Any]) -> None:
    create = next(line for line in run_scripts().splitlines() if "gh pr create" in line)
    assert ADMIN_SETTING in create


@then("the dependency audit workflow never merges a pull request")
def never_merges(ctx: dict[str, Any]) -> None:
    scripts = run_scripts()
    for forbidden in (r"gh\s+pr\s+merge", r"--auto\b", r"/merge\b", r"enablePullRequestAutoMerge"):
        assert not re.search(forbidden, scripts), forbidden


@then(parsers.parse('it never applies the "{a}" or "{b}" labels'))
def never_labels(ctx: dict[str, Any], a: str, b: str) -> None:
    scripts = run_scripts()
    for label in (a, b):
        assert label not in scripts
    assert not re.search(r"--(add-)?label", scripts)


@then(parsers.parse('the dependency audit opens its pull request from "{branch}" as a draft'))
def opens_draft(ctx: dict[str, Any], branch: str) -> None:
    assert job()["env"]["BRANCH"] == branch
    create = next(line for line in run_scripts().splitlines() if "gh pr create" in line)
    assert "--draft" in create
    assert '--head "$BRANCH"' in create
    assert "--base main" in create


@then("an updated pull request is turned back into a draft")
def back_to_draft(ctx: dict[str, Any]) -> None:
    assert re.search(r"gh\s+pr\s+ready\s+\"?\$PR\"?\s+--undo", run_scripts())


@then("the dependency audit runs the pip-audit export and audit of ci.yml for backend and infra")
def same_pip_audit(ctx: dict[str, Any]) -> None:
    ci = (WF / "ci.yml").read_text()
    export = re.search(r"uv export [^\n]+", ci).group(0).split(" -o ")[0]
    pin = re.search(r'"pip-audit==[0-9.]+"', ci).group(0)
    steps = {s.get("name", ""): s for s in job()["steps"]}
    for project in ("backend", "infra"):
        step = next(s for n, s in steps.items() if n.startswith(f"pip-audit {project}"))
        assert step["working-directory"] == project
        assert export.replace(" --no-dev", "") in step["run"].replace(" --no-dev", "")
        assert "pip-audit --requirement" in step["run"]
        assert "--disable-pip" in step["run"]
        assert "--format json" in step["run"]
    assert (
        "--no-dev" in next(s for n, s in steps.items() if n.startswith("pip-audit backend"))["run"]
    )
    assert pin in run_scripts()


@then(parsers.parse('it runs "{command}" for web'))
def pnpm_audit(ctx: dict[str, Any], command: str) -> None:
    step = next(s for s in job()["steps"] if command in s.get("run", ""))
    assert step["working-directory"] == "web"
