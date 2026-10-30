"""Binds tests/features/ci_scheduled_red_notice.feature (ADR-0053-0049; retro C4; ADR 0053).

The REAL `run:` scripts of .github/workflows/dependency-audit.yml and
.github/workflows/scheduled-red-notice.yml run with `bash -eo pipefail` (as Actions runs them)
on a throwaway git checkout whose `origin` is a local bare repository, with a recording `uv`
(moves the locked version as `uv lock --upgrade-package` would) and a recording `gh` on PATH.
Only the pip-audit/pnpm audit steps are replaced: their JSON reports are planted in $OUT.
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]
scenarios("ci_scheduled_red_notice.feature")

WF = REPO_ROOT / ".github" / "workflows"
AUDIT_STEPS = (
    "Start from the upgrade branch merged with main (or from main)",
    "Upgrade vulnerable Python packages (scripts/ci/security_upgrade.py)",
    "Commit and push the upgrade branch",
    "Open or update the draft upgrade pull request",
)
NOTICE_STEPS = (
    "Decide the notice (scripts/ci/scheduled_red_notice.py)",
    "Open, comment on or close the notice issue",
)
OWNER = "nhuthuynh"
RUN_URL = "https://github.com/nhuthuynh/racket-analytics/actions/runs/123"
SHA = "ab" * 20

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

# A recording `gh`: logs argv (and the body file's text); answers `pr list` / `issue list` with
# the number in FAKE_GH_PR / FAKE_GH_ISSUE (empty = none open), as the real --jq filter would.
FAKE_GH = r"""
import json, os, sys
args = sys.argv[1:]
entry = {"args": args}
for flag in ("--body-file",):
    if flag in args:
        entry["body"] = open(args[args.index(flag) + 1]).read()
with open(os.environ["FAKE_GH_LOG"], "a") as log:
    log.write(json.dumps(entry) + "\n")
if args[:2] == ["pr", "list"]:
    print(os.environ.get("FAKE_GH_PR", ""))
elif args[:2] == ["issue", "list"]:
    print(os.environ.get("FAKE_GH_ISSUE", ""))
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


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def make_bin(tmp: Path) -> Path:
    fake = tmp / "bin"
    fake.mkdir()
    for name, code in (("uv", FAKE_UV), ("gh", FAKE_GH)):
        (tmp / f"fake_{name}.py").write_text(code)
        exe = fake / name
        exe.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{tmp / f"fake_{name}.py"}" "$@"\n')
        exe.chmod(0o755)
    (fake / "python3").symlink_to(sys.executable)
    return fake


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    runner_temp = tmp_path / "runner"
    runner_temp.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    return {
        "tmp": tmp_path,
        "bin": make_bin(tmp_path),
        "runner_temp": runner_temp,
        "home": home,
        "gh_log": tmp_path / "gh.log",
        "uv_log": tmp_path / "uv.log",
        "fix_to": {},
        "env": {},
    }


def base_env(ctx: dict[str, Any]) -> dict[str, str]:
    return {
        "PATH": f"{ctx['bin']}:/usr/bin:/bin",
        "HOME": str(ctx["home"]),
        "GIT_CONFIG_NOSYSTEM": "1",
        "RUNNER_TEMP": str(ctx["runner_temp"]),
        "FAKE_GH_LOG": str(ctx["gh_log"]),
        "FAKE_UV_LOG": str(ctx["uv_log"]),
        "FAKE_UV_TO": json.dumps(ctx["fix_to"]),
        "GH_TOKEN": "not-a-real-token",
        **ctx["env"],
    }


def gh_calls(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    if not ctx["gh_log"].exists():
        return []
    return [json.loads(line) for line in ctx["gh_log"].read_text().splitlines()]


def workflow(name: str) -> dict[str, Any]:
    return yaml.safe_load((WF / name).read_text())


def only_job(name: str) -> dict[str, Any]:
    jobs = workflow(name)["jobs"]
    assert len(jobs) == 1, list(jobs)
    return next(iter(jobs.values()))


def step(job: dict[str, Any], name: str) -> dict[str, Any]:
    found = [s for s in job["steps"] if s.get("name") == name]
    assert len(found) == 1, f"no single step named {name!r}"
    return found[0]


def run_step(
    script: str, cwd: Path, env: dict[str, str], gh_env: Path, gh_out: Path
) -> subprocess.CompletedProcess[str]:
    """Run one `run:` script as Actions does, then apply what it wrote to $GITHUB_ENV."""
    env = {**env, "GITHUB_ENV": str(gh_env), "GITHUB_OUTPUT": str(gh_out)}
    for line in gh_env.read_text().splitlines() if gh_env.exists() else []:
        key, _, value = line.partition("=")
        env[key] = value
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


# ------------------------------------------------------------------ dependency audit
@given(parsers.parse('a checkout whose backend lock lists "{pkg}" at "{version}"'))
def checkout(ctx: dict[str, Any], pkg: str, version: str) -> None:
    origin = ctx["tmp"] / "origin.git"
    repo = ctx["tmp"] / "repo"
    git(ctx["tmp"], "init", "-q", "--bare", "-b", "main", str(origin))
    (repo / "backend").mkdir(parents=True)
    (repo / "infra").mkdir()
    (repo / "scripts" / "ci").mkdir(parents=True)
    shutil.copy(SCRIPTS_DIR / "ci" / "security_upgrade.py", repo / "scripts" / "ci")
    (repo / "backend" / "uv.lock").write_text(lock_text({pkg: version, "idna": "3.10"}))
    (repo / "infra" / "uv.lock").write_text(lock_text({"pyyaml": "6.0.3"}))
    git(ctx["tmp"], "init", "-q", "-b", "main", str(repo))
    git(repo, "-c", "user.name=t", "-c", "user.email=t@e", "add", ".")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-q", "-m", "base")
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "-q", "origin", "main")
    ctx["repo"], ctx["origin"] = repo, origin


def plant(ctx: dict[str, Any], deps: list[dict[str, Any]]) -> None:
    out = ctx["runner_temp"] / "deps-audit"
    out.mkdir(exist_ok=True)
    (out / "backend.json").write_text(json.dumps({"dependencies": deps, "fixes": []}))
    clean_infra = [{"name": "pyyaml", "version": "6.0.3", "vulns": []}]
    (out / "infra.json").write_text(json.dumps({"dependencies": clean_infra, "fixes": []}))
    (out / "web.json").write_text(json.dumps({"actions": [], "advisories": {}, "metadata": {}}))


@given(
    parsers.parse(
        'a planted pip-audit advisory "{advisory}" against "{pkg}" "{version}" fixed in "{fix}"'
    )
)
def planted(ctx: dict[str, Any], advisory: str, pkg: str, version: str, fix: str) -> None:
    ctx["fix_to"][pkg] = fix
    vuln = {"id": advisory, "fix_versions": [fix], "aliases": [], "description": "planted"}
    plant(ctx, [{"name": pkg, "version": version, "vulns": [vuln]}])


@given("pip-audit finds nothing")
def finds_nothing(ctx: dict[str, Any]) -> None:
    plant(ctx, [{"name": "certifi", "version": "2026.10.19", "vulns": []}])


@given("no upgrade pull request is open")
def no_pr(ctx: dict[str, Any]) -> None:
    ctx["env"]["FAKE_GH_PR"] = ""


@given(parsers.parse("upgrade pull request {number:d} is open"))
def pr_open(ctx: dict[str, Any], number: int) -> None:
    ctx["env"]["FAKE_GH_PR"] = str(number)


@when("the dependency audit workflow's upgrade, push and pull request steps run")
def run_audit(ctx: dict[str, Any]) -> None:
    job = only_job("dependency-audit.yml")
    env = {**base_env(ctx), **{k: str(v) for k, v in job.get("env", {}).items()}}
    gh_env, gh_out = ctx["tmp"] / "github_env", ctx["tmp"] / "github_output"
    ctx["today"] = dt.datetime.now(dt.UTC).date().isoformat()
    for name in AUDIT_STEPS:
        s = step(job, name)
        if s.get("if") == "steps.push.outputs.pushed == 'true'":
            outputs = gh_out.read_text() if gh_out.exists() else ""
            if "pushed=true" not in outputs.splitlines():
                continue
        else:
            assert "if" not in s, (name, s["if"])
        res = run_step(s["run"], ctx["repo"], {**env, **s.get("env", {})}, gh_env, gh_out)
        assert res.returncode == 0, (name, res.stdout, res.stderr)


@then(parsers.parse('the branch "{branch}" on origin locks "{pkg}" at "{version}"'))
def origin_locks(ctx: dict[str, Any], branch: str, pkg: str, version: str) -> None:
    lock = git(ctx["origin"], "show", f"{branch}:backend/uv.lock")
    assert f'name = "{pkg}"\nversion = "{version}"' in lock
    assert git(ctx["origin"], "rev-parse", "main") in git(
        ctx["origin"], "rev-list", branch
    ).splitlines()  # built on main, not a rewrite of it


@then(
    parsers.parse(
        'gh opened a draft pull request into "{base}" from "{head}" titled with today\'s UTC date'
    )
)
def opened_draft(ctx: dict[str, Any], base: str, head: str) -> None:
    (create,) = [c["args"] for c in gh_calls(ctx) if c["args"][:2] == ["pr", "create"]]
    assert "--draft" in create
    assert create[create.index("--base") + 1] == base
    assert create[create.index("--head") + 1] == head
    assert create[create.index("--title") + 1] == f"[DEPS-AUDIT] security upgrades {ctx['today']}"


@then(parsers.parse("gh edited pull request {number:d} and turned it back into a draft"))
def edited_and_drafted(ctx: dict[str, Any], number: int) -> None:
    args = [c["args"] for c in gh_calls(ctx)]
    assert any(a[:3] == ["pr", "edit", str(number)] for a in args), args
    assert ["pr", "ready", str(number), "--undo"] in args


@then("gh opened no new pull request")
def no_new_pr(ctx: dict[str, Any]) -> None:
    assert not [c for c in gh_calls(ctx) if c["args"][:2] == ["pr", "create"]]


@then(parsers.parse('origin has no branch "{branch}"'))
def no_branch(ctx: dict[str, Any], branch: str) -> None:
    assert git(ctx["origin"], "branch", "--list", branch) == ""


@then("gh was not asked to open or edit a pull request")
def no_pr_calls(ctx: dict[str, Any]) -> None:
    assert not [c for c in gh_calls(ctx) if c["args"][0] == "pr"]


# ------------------------------------------------------------------ scheduled red notice
@given("no notice issue is open")
def no_issue(ctx: dict[str, Any]) -> None:
    ctx["env"]["FAKE_GH_ISSUE"] = ""


@given(parsers.parse("notice issue {number:d} is open"))
def issue_open(ctx: dict[str, Any], number: int) -> None:
    ctx["env"]["FAKE_GH_ISSUE"] = str(number)


def run_notice(ctx: dict[str, Any], event_values: dict[str, str]) -> subprocess.CompletedProcess:
    job = only_job("scheduled-red-notice.yml")
    env = {**base_env(ctx), "PO": OWNER, "GH_REPO": "nhuthuynh/racket-analytics", **event_values}
    gh_env, gh_out = ctx["tmp"] / "github_env", ctx["tmp"] / "github_output"
    res: subprocess.CompletedProcess[str] | None = None
    for name in NOTICE_STEPS:
        s = step(job, name)
        res = run_step(s["run"], REPO_ROOT, env, gh_env, gh_out)
        if res.returncode != 0:
            return res
    assert res is not None
    return res


def event(workflow_name: str, ev: str, conclusion: str, url: str = RUN_URL) -> dict[str, str]:
    return {"WORKFLOW": workflow_name, "EVENT": ev, "CONCLUSION": conclusion, "RUN_URL": url,
            "SHA": SHA}  # fmt: skip


@when(parsers.parse('the scheduled "{name}" run ends with "{conclusion}"'))
def scheduled_ends(ctx: dict[str, Any], name: str, conclusion: str) -> None:
    res = run_notice(ctx, event(name, "schedule", conclusion))
    assert res.returncode == 0, res.stdout + res.stderr


@when(parsers.parse('a "{ev}" run of "{name}" ends with "{conclusion}"'))
def other_run_ends(ctx: dict[str, Any], ev: str, name: str, conclusion: str) -> None:
    res = run_notice(ctx, event(name, ev, conclusion))
    assert res.returncode == 0, res.stdout + res.stderr


@when("the notice step runs without a run URL", target_fixture="result")
def without_url(ctx: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    return run_notice(ctx, event("CI", "schedule", "failure", url=""))


@then(
    parsers.parse('gh opened an issue titled "{title}" assigned to the repository owner')
)  # fmt: skip
def opened_issue(ctx: dict[str, Any], title: str) -> None:
    (create,) = [c for c in gh_calls(ctx) if c["args"][:2] == ["issue", "create"]]
    args = create["args"]
    assert args[args.index("--title") + 1] == title
    assert args[args.index("--assignee") + 1] == OWNER
    ctx["issue_body"] = create["body"]


@then("the issue body links the failed run and names the commit")
def body_links(ctx: dict[str, Any]) -> None:
    assert RUN_URL in ctx["issue_body"]
    assert SHA in ctx["issue_body"]


@then(parsers.parse("gh commented on issue {number:d} with the failed run"))
def commented(ctx: dict[str, Any], number: int) -> None:
    (comment,) = [c for c in gh_calls(ctx) if c["args"][:3] == ["issue", "comment", str(number)]]
    assert RUN_URL in comment["body"]


@then("gh opened no new issue")
def no_new_issue(ctx: dict[str, Any]) -> None:
    assert not [c for c in gh_calls(ctx) if c["args"][:2] == ["issue", "create"]]


@then(parsers.parse("gh closed issue {number:d} naming the green run"))
def closed(ctx: dict[str, Any], number: int) -> None:
    (close,) = [c for c in gh_calls(ctx) if c["args"][:3] == ["issue", "close", str(number)]]
    assert RUN_URL in close["body"]


@then("gh was not asked to open, comment on or close an issue")
def no_issue_writes(ctx: dict[str, Any]) -> None:
    writes = {"create", "comment", "close", "edit", "reopen"}
    assert not [c for c in gh_calls(ctx) if c["args"][0] == "issue" and c["args"][1] in writes]


@then(parsers.parse('the notice job fails naming "{flag}"'))
def notice_fails(result: subprocess.CompletedProcess[str], flag: str) -> None:
    assert result.returncode != 0
    assert flag in result.stdout + result.stderr


@then(parsers.parse('the notice workflow runs on the completion of every workflow with a "{trigger}" trigger'))  # fmt: skip
def listens(ctx: dict[str, Any], trigger: str) -> None:
    scheduled = set()
    for path in sorted(WF.glob("*.yml")):
        doc = yaml.safe_load(path.read_text())
        if trigger in (doc.get(True) or {}):  # PyYAML reads `on:` as True
            scheduled.add(doc["name"])
    assert scheduled >= {"CI", "Nightly quality", "Dependency audit"}, scheduled
    on = workflow("scheduled-red-notice.yml")[True]
    assert set(on) == {"workflow_run"}
    assert set(on["workflow_run"]["workflows"]) == scheduled
    assert on["workflow_run"]["types"] == ["completed"]


@then("its job runs only for scheduled runs")
def only_scheduled(ctx: dict[str, Any]) -> None:
    job = only_job("scheduled-red-notice.yml")
    assert job["if"] == "github.event.workflow_run.event == 'schedule'"
    assert job["env"] == {
        "WORKFLOW": "${{ github.event.workflow_run.name }}",
        "EVENT": "${{ github.event.workflow_run.event }}",
        "CONCLUSION": "${{ github.event.workflow_run.conclusion }}",
        "RUN_URL": "${{ github.event.workflow_run.html_url }}",
        "SHA": "${{ github.event.workflow_run.head_sha }}",
        "PO": "${{ github.repository_owner }}",
        "GH_REPO": "${{ github.repository }}",
    }


@then("the notice job may only read contents and write issues")
def notice_privilege(ctx: dict[str, Any]) -> None:
    assert workflow("scheduled-red-notice.yml")["permissions"] == {}
    assert only_job("scheduled-red-notice.yml")["permissions"] == {
        "contents": "read",
        "issues": "write",
    }


@then("only the step that calls GitHub gets the token")
def notice_token(ctx: dict[str, Any]) -> None:
    job = only_job("scheduled-red-notice.yml")
    with_token = [s["name"] for s in job["steps"] if "GH_TOKEN" in s.get("env", {})]
    assert with_token == ["Open, comment on or close the notice issue"]
    checkouts = [s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout@")]
    assert [s["with"]["persist-credentials"] for s in checkouts] == [False]


@then("the notice workflow never merges, labels or pushes")
def notice_never(ctx: dict[str, Any]) -> None:
    scripts = "\n".join(s.get("run", "") for s in only_job("scheduled-red-notice.yml")["steps"])
    for forbidden in (r"gh pr", "git push", "--label", "--add-label", "merge"):
        assert forbidden not in scripts, forbidden
