"""Binds tests/features/ops_disk_precheck.feature (OPS-DISK-06): `make` run for real with a
stand-in for Compose, and the worktree report run as the SRE runs it, on real git worktrees in
a temp dir against a local HTTP stand-in for the GitHub pulls API."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("ops_disk_precheck.feature")

REPORT = SCRIPTS_DIR / "ops" / "worktree_report.py"
MARK = "COMPOSE-STAND-IN-RAN"


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    return {"dir": tmp_path, "prs": {}, "make": []}


@pytest.fixture
def pulls_api(ctx: dict[str, Any]) -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            head = parse_qs(urlsplit(self.path).query).get("head", [""])[0]
            branch = head.split(":", 1)[-1]
            body = json.dumps(ctx["prs"].get(branch, [])).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def _make(ctx: dict[str, Any], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "-C", str(REPO_ROOT), *args, f"ENV_FILE={ctx['dir'] / '.env'}"],
        capture_output=True,
        text=True,
        timeout=60,
    )


@when('the recipe of "make up" is listed with make -n')
def list_up(ctx: dict[str, Any]) -> None:
    ctx["lines"] = _make(ctx, "-n", "up").stdout.splitlines()


@then(parsers.parse('"{precheck}" comes before the Compose build'))
def precheck_first(ctx: dict[str, Any], precheck: str) -> None:
    lines = ctx["lines"]
    build = next(i for i, line in enumerate(lines) if "--build" in line)
    assert any(precheck in line for line in lines[:build]), lines


@given("a build floor no disk can meet")
def huge_floor(ctx: dict[str, Any]) -> None:
    ctx["make"] = ["BUILD_MIN_FREE_GB=1000000"]


@when('"make up" runs with a stand-in for Compose')
def run_up(ctx: dict[str, Any]) -> None:
    ctx["res"] = _make(ctx, "up", f"COMPOSE=echo {MARK}", *ctx["make"])


@then("make fails and the stand-in for Compose never ran")
def stopped(ctx: dict[str, Any]) -> None:
    res = ctx["res"]
    assert res.returncode != 0, res
    assert MARK not in res.stdout, res.stdout
    assert "need >= 1000000 GB" in res.stderr


def _git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, capture_output=True)


@given(parsers.parse('a worktree on branch "{branch}" whose pull request is {state}'))
def worktree(ctx: dict[str, Any], branch: str, state: str) -> None:
    repo = ctx["dir"] / "repo"
    if not repo.exists():
        _git("init", "-q", "-b", "main", str(repo))
        _git("-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
             "--allow-empty", "-m", "init")  # fmt: skip
    path = ctx["dir"] / "wt" / branch.replace("/", "_")
    _git("-C", str(repo), "worktree", "add", "-q", "-b", branch, str(path))
    merged = "2026-11-12T00:00:00Z" if state == "merged" else None
    pr_state = "open" if state == "open" else "closed"
    ctx["prs"][branch] = [{"number": 1, "state": pr_state, "merged_at": merged}]


@when("the worktree report runs")
def run_report(ctx: dict[str, Any], pulls_api: str) -> None:
    res = subprocess.run(
        [sys.executable, str(REPORT), "--root", str(ctx["dir"] / "wt"), "--json"],
        capture_output=True,
        text=True,
        timeout=60,
        env={"GITHUB_API_URL": pulls_api, "PATH": "/usr/bin:/bin"},
    )
    assert res.returncode == 0, res
    ctx["rows"] = {row["branch"]: row for row in json.loads(res.stdout)}


@then(parsers.parse('the worktree on "{branch}" is listed as "{action}"'))
def listed(ctx: dict[str, Any], branch: str, action: str) -> None:
    assert ctx["rows"][branch]["action"] == action, ctx["rows"]
