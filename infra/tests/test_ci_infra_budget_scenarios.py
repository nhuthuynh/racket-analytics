"""Binds tests/features/ci_infra_budget.feature (CI-INFRA-BUDGET; ST-002; PO 2026-10-29).

Incident: push CI on main 5bba847 (run 40908731812), infra-tests cancelled by its 10-minute
timeout after "1717 passed in 581.90s". The fix runs the suite with pytest-xdist; this binding
reads the real ci.yml, pyproject.toml and uv.lock, and runs two copies of the real
scripts/dev-objectstore.sh at once against a fake slow download to prove the shared SeaweedFS
download cache is written by one worker at a time.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]
scenarios("ci_infra_budget.feature")

INFRA = REPO_ROOT / "infra"
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def infra_job() -> dict:
    return yaml.safe_load(CI.read_text())["jobs"]["infra-tests"]


def pytest_command() -> str:
    runs = [s["run"] for s in infra_job()["steps"] if "pytest" in s.get("run", "")]
    assert len(runs) == 1, runs
    return runs[0]


# ---------------------------------------------------------------- Rule: parallel, no test dropped
@when("the infra job's pytest command is read from the CI workflow", target_fixture="command")
def read_command() -> str:
    return pytest_command()


@then(parsers.parse('it runs with "{workers}" and distributes whole test files with "{dist}"'))
def runs_parallel(command: str, workers: str, dist: str) -> None:
    assert workers in command, f"infra pytest runs serially: {command!r}"
    assert dist in command, f"infra pytest does not keep a file's tests on one worker: {command!r}"


@then(parsers.parse('it still selects the tests marked "{expr}"'))
def same_selection(command: str, expr: str) -> None:
    assert f'-m "{expr}"' in command, command


@then(
    parsers.parse(
        '"{package}" is a dev dependency in infra/pyproject.toml and pinned in infra/uv.lock'
    )
)
def locked_dependency(package: str) -> None:
    dev = tomllib.loads((INFRA / "pyproject.toml").read_text())["dependency-groups"]["dev"]
    assert any(d.split(">")[0].split("=")[0].strip() == package for d in dev), dev
    lock = tomllib.loads((INFRA / "uv.lock").read_text())
    assert package in {p["name"] for p in lock["package"]}, "not pinned in infra/uv.lock"


@then(parsers.parse("the infra job's timeout is between {low:d} and {high:d} minutes"))
def timeout_headroom(low: int, high: int) -> None:
    assert low <= infra_job()["timeout-minutes"] <= high


# ---------------------------------------------------------------- Rule: no half-written shared file
# A fake `curl` that marks itself active, waits, records how many downloads were active at once,
# then fails (so no real binary is fetched and the script dies with "download failed").
FAKE_CURL = """#!/bin/bash
active="$FAKE_DL_DIR/active"
mkdir -p "$active"
touch "$active/$$"
sleep 1.5
ls "$active" | wc -l >> "$FAKE_DL_DIR/overlap"
rm -f "$active/$$"
exit 22
"""


@given("an empty SeaweedFS download cache and a slow download", target_fixture="sandbox")
def sandbox(tmp_path: Path) -> Path:
    # The script derives its download cache from its own location (<root>/.local/bin), so a copy
    # under tmp_path/scripts has a private, empty cache and never touches the checkout's one.
    (tmp_path / "scripts").mkdir()
    shutil.copy2(SCRIPTS_DIR / "dev-objectstore.sh", tmp_path / "scripts" / "dev-objectstore.sh")
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    (fakebin / "curl").write_text(FAKE_CURL)
    (fakebin / "curl").chmod(0o755)
    (tmp_path / "dl").mkdir()
    return tmp_path


@when("two test workers start the dev object store at the same time", target_fixture="starts")
def two_starts(sandbox: Path) -> list[subprocess.CompletedProcess[str]]:
    env = {
        "PATH": f"{sandbox / 'fakebin'}:/usr/bin:/bin",
        "HOME": str(sandbox),
        "FAKE_DL_DIR": str(sandbox / "dl"),
    }
    procs = [
        subprocess.Popen(
            ["bash", str(sandbox / "scripts" / "dev-objectstore.sh"), "start"],
            env={**env, "RA_DEV_STATE": str(sandbox / f"state{i}")},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for i in range(2)
    ]
    done = []
    for p in procs:
        out, err = p.communicate(timeout=60)
        done.append(subprocess.CompletedProcess(p.args, p.returncode, out, err))
    return done


@then("the two downloads never overlap")
def no_overlap(sandbox: Path, starts: list[subprocess.CompletedProcess[str]]) -> None:
    for res in starts:  # the fake download fails, so each start must fail closed
        assert res.returncode != 0, res.stderr
        assert "download failed" in res.stderr, res.stderr
    counts = (sandbox / "dl" / "overlap").read_text().split()
    assert len(counts) == 2, counts
    assert max(int(c) for c in counts) == 1, f"downloads active at once: {counts}"
    cache = sandbox / ".local" / "bin"
    leftovers = [n for n in os.listdir(cache) if n.endswith(".tgz")] if cache.is_dir() else []
    assert leftovers == [], f"a partial download was left in the cache: {leftovers}"
