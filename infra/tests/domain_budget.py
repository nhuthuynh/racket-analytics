"""Helpers for the CI-DOMAIN-BUDGET tests (sre-devops-engineer; NFR-073; ADR 0049).

Reads the budgeted domain step exactly as ci.yml declares it, expands the workflow env the way
the runner's shell does, and runs it in ``backend`` with the backend's own environment.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO_ROOT

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
BACKEND = REPO_ROOT / "backend"
BUDGET_VAR = "DOMAIN_UNIT_BUDGET_S"


def workflow() -> dict[str, Any]:
    return yaml.safe_load(CI.read_text())


def ci_env() -> dict[str, str]:
    return {k: str(v) for k, v in workflow()["env"].items()}


def unit_steps() -> list[dict[str, Any]]:
    return workflow()["jobs"]["python-unit"]["steps"]


def domain_step() -> dict[str, Any]:
    steps = [s for s in unit_steps() if f'"${BUDGET_VAR}"' in s.get("run", "")]
    assert len(steps) == 1, f"expected one budgeted domain step, got {len(steps)}"
    return steps[0]


def domain_line(run: str | None = None) -> str:
    run = domain_step()["run"] if run is None else run
    lines = [ln for ln in run.splitlines() if "run_with_budget.py" in ln]
    assert len(lines) == 1, lines
    return lines[0].strip()


def expand(line: str, env: dict[str, str]) -> list[str]:
    """Shell-like: "$VAR" stays one word, a bare $VAR splits on spaces (the step's SC2086)."""
    quoted = re.sub(r'"\$(\w+)"', lambda m: shlex.quote(env[m.group(1)]), line)
    bare = re.sub(r"\$(\w+)", lambda m: env[m.group(1)], quoted)
    return shlex.split(bare)


def budget_argv(run: str | None = None) -> list[str]:
    """argv of run_with_budget.py up to ``--`` (budget and options)."""
    argv = expand(domain_line(run), ci_env())
    start = next(i for i, a in enumerate(argv) if a.endswith("run_with_budget.py"))
    return argv[start + 1 : argv.index("--")]


def command(run: str | None = None) -> list[str]:
    """The budgeted command (after ``--``), as the runner executes it in ``backend``."""
    argv = expand(domain_line(run), ci_env())
    return argv[argv.index("--") + 1 :]


def pytest_args(run: str | None = None) -> list[str]:
    cmd = command(run)
    return cmd[cmd.index("pytest") + 1 :]


def option(args: list[str], name: str) -> str | None:
    for i, a in enumerate(args):
        if a == name and i + 1 < len(args):
            return args[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return None


def positionals(args: list[str]) -> list[str]:
    """Paths given to pytest: words that are neither options nor option values."""
    takes_value = {"-m", "-n", "--dist", "-p", "-k", "--junitxml", "-o", "--maxfail"}
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif a in takes_value:
            skip = True
        elif not a.startswith("-"):
            out.append(a)
    return out


NARROWING = ("-k", "--deselect", "--ignore", "--ignore-glob", "--lf", "--last-failed", "--sw",
             "--stepwise", "-x", "--exitfirst", "--maxfail", "--co", "--collect-only")  # fmt: skip


def narrowing(args: list[str]) -> list[str]:
    """Flags that would change what runs: deselection, early stop, plugins off, ini overrides."""
    return [a for a in args if a.split("=", 1)[0] in NARROWING or a == "-o" or a.startswith("-p")]


def profile_set() -> bool:
    step = domain_step()
    return "HYPOTHESIS_PROFILE" in step["run"] or "HYPOTHESIS_PROFILE" in step.get("env", {})


# ---------------------------------------------------------------- real runs (scenario)
def _backend_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in {"VIRTUAL_ENV", "HYPOTHESIS_PROFILE"}}
    env.pop("APP_ENV", None)
    return env


def run_in_backend(cmd: list[str], timeout: float = 300) -> subprocess.CompletedProcess[str]:
    if shutil.which("uv") is None:
        pytest.fail("uv not on PATH (CI: pip install uv) - fails closed, no skip")
    # --no-sync in ci.yml expects a synced backend env (the job runs `uv sync --locked` first).
    sync = subprocess.run(["uv", "sync", "--locked", "--quiet"], cwd=BACKEND, env=_backend_env(),
                          capture_output=True, text=True, timeout=600)  # fmt: skip
    assert sync.returncode == 0, sync.stderr
    return subprocess.run(cmd, cwd=BACKEND, env=_backend_env(), capture_output=True, text=True,
                          timeout=timeout)  # fmt: skip


def junit_outcomes(path: Path) -> dict[str, str]:
    """test id -> passed | failed | error | skipped, from a pytest junit file."""
    out: dict[str, str] = {}
    root = ET.parse(path).getroot()  # noqa: S314 - the junit file our own pytest run wrote
    for case in root.iter("testcase"):
        tid = f"{case.get('classname')}::{case.get('name')}"
        kinds = [c.tag for c in case]
        outcome = next((k for k in ("failure", "error", "skipped") if k in kinds), "passed")
        out[tid] = {"failure": "failed"}.get(outcome, outcome)
    return out
