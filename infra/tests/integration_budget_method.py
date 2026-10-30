"""FIX-04-4a (VERIFY04R4-01): the goal-scorecard's integration budget line and CI's NFR-073 gate.

NFR-073 times the integration job's backend suites (600 s). Since ADR 0048 CI runs them in
parallel workers (``pytest -n auto``) after migrating the base database once, outside the budget.
Sprint 3's §4 G03-11 (d) line, which Sprint 4's §4 G04-11 inherited, still times one serial
process (``pytest -q -m integration tests/integration``). On a 4-core host that run takes more
than 600 s (VERIFY-04-r3 and -r4: rc 124) while the gate's own form takes about 3 min, so the
scorecard measured a different suite from the one the gate times (the G02-12 domain-budget
defect again, for the integration budget).

These helpers read both commands from the files the verifier and CI read, so the tests compare
the real method with the real gate.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any

import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
SCORECARD_03 = REPO_ROOT / "docs" / "sprints" / "03" / "goal-scorecard.md"
SCORECARD_04 = REPO_ROOT / "docs" / "sprints" / "04" / "goal-scorecard.md"
BUDGET_MARK = "$INTEGRATION_BUDGET_S"
MIGRATE = "python -m racket.platform.migrate"
# Options whose value is only where a report is written; the verifier writes under $GOAL.
OUTPUT_OPTIONS = ("--json", "--junitxml", "--cov-report")


# ---------------------------------------------------------------- reading the two sources
def ci_env() -> dict[str, str]:
    env: dict[str, str] = yaml.safe_load(CI.read_text())["env"]
    return env


def integration_steps() -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = yaml.safe_load(CI.read_text())["jobs"]["integration"]["steps"]
    return steps


def ci_budgeted_run() -> str:
    """The `run:` of CI's budgeted backend-suites step, with the budget variable resolved."""
    runs = [s["run"] for s in integration_steps() if BUDGET_MARK in s.get("run", "")]
    assert len(runs) == 1, runs
    return runs[0].replace(f'"{BUDGET_MARK}"', ci_env()["INTEGRATION_BUDGET_S"])


def ci_migrate_run() -> str:
    runs = [s["run"] for s in integration_steps() if MIGRATE in s.get("run", "")]
    assert len(runs) == 1, runs
    return str(runs[0])


def bash_blocks(text: str) -> list[str]:
    return re.findall(r"```bash\n(.*?)```", text, flags=re.S)


def logical_lines(block: str) -> list[str]:
    """Shell lines with backslash continuations joined and trailing comments kept."""
    return [ln.strip() for ln in re.sub(r"\\\n\s*", " ", block).splitlines() if ln.strip()]


def g03_11_section() -> str:
    return SCORECARD_03.read_text().split("### G03-11:", 1)[1].split("### G03-12:", 1)[0]


def g04_11_section() -> str:
    return SCORECARD_04.read_text().split("- **G04-11:**", 1)[1].split("- **G04-12:**", 1)[0]


def budget_lines(section: str, budget: str) -> list[str]:
    return [
        ln
        for block in bash_blocks(section)
        for ln in logical_lines(block)
        if re.search(rf"run_with_budget\.py {budget} ", ln)
    ]


def g03_11_integration_line() -> str:
    lines = budget_lines(g03_11_section(), ci_env()["INTEGRATION_BUDGET_S"])
    assert len(lines) == 1, lines
    return lines[0]


# ---------------------------------------------------------------- comparing argv
def pytest_argv(command: str) -> list[str]:
    """The pytest arguments a budget command runs (after `pytest`), output paths dropped."""
    words = shlex.split(command.split("; echo rc=", 1)[0].split(" # ", 1)[0])
    return normalise(words[words.index("pytest") + 1 :])


def normalise(args: list[str]) -> list[str]:
    out: list[str] = []
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        if a in OUTPUT_OPTIONS:
            skip = True
            continue
        if a.startswith(tuple(f"{o}=" for o in OUTPUT_OPTIONS)):
            continue
        out.append(a)
    return out


def marker_expression(args: list[str]) -> str | None:
    return args[args.index("-m") + 1] if "-m" in args else None


def ignores(args: list[str]) -> set[str]:
    return {a for a in args if a.startswith(("--ignore=", "--ignore-glob="))}


def integration_budget_problems(command: str) -> list[str]:
    """Why a scorecard integration-budget line does not time CI's NFR-073 gate; [] when it does."""
    problems: list[str] = []
    budget = ci_env()["INTEGRATION_BUDGET_S"]
    if not re.search(rf"run_with_budget\.py {budget} ", command):
        problems.append(f"budget is not CI's INTEGRATION_BUDGET_S ({budget} s)")
    if "pytest" not in command:
        return [*problems, "no pytest run"]
    mine, gate = pytest_argv(command), pytest_argv(ci_budgeted_run())
    if not ("-n" in mine and mine[mine.index("-n") + 1] == "auto"):
        problems.append("one serial process, not CI's parallel workers (-n auto, ADR 0048)")
    if marker_expression(mine) != marker_expression(gate):
        problems.append(
            f"selection -m {marker_expression(mine)!r} is not CI's {marker_expression(gate)!r}"
        )
    if ignores(mine) != ignores(gate):
        problems.append(f"ignores {sorted(ignores(mine))} are not CI's {sorted(ignores(gate))}")
    if ("--cov" in mine) != ("--cov" in gate):
        problems.append("coverage inside the budget differs from CI's")
    return problems


# ---------------------------------------------------------------- running the commands
RECORDER = """#!/usr/bin/env bash
# Stands in for `uv`: records what the method would run, runs nothing.
printf '%s\\n' "$(printf '%q ' "$@")" >> "$UV_CALLS"
"""


def recorded_calls(script: str, tmp_path: Path, name: str) -> list[list[str]]:
    """Run `script` with real bash and the real run_with_budget.py in a scratch repo layout
    (backend/, scripts/ci/), with `uv` replaced by a recorder; return each `uv` call's argv."""
    root = tmp_path / name
    (root / "backend").mkdir(parents=True)
    (root / "scripts" / "ci").mkdir(parents=True)
    shutil.copy(SCRIPTS_DIR / "ci" / "run_with_budget.py", root / "scripts" / "ci")
    bindir = root / "bin"
    bindir.mkdir()
    uv = bindir / "uv"
    uv.write_text(RECORDER)
    uv.chmod(uv.stat().st_mode | stat.S_IEXEC)
    calls = root / "uv-calls.txt"
    calls.touch()
    env = {
        **os.environ,
        "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}",
        "UV_CALLS": str(calls),
        "GOAL": str(root / "goal"),
    }
    proc = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return [shlex.split(ln) for ln in calls.read_text().splitlines()]


def uv_pytest_args(call: list[str]) -> list[str] | None:
    """`uv run [--no-sync] pytest ARGS` -> ARGS (output paths dropped); None for other calls."""
    words = [w for w in call if w != "--no-sync"]
    if words[:2] != ["run", "pytest"]:
        return None
    return normalise(words[2:])


def ci_script() -> str:
    """CI's migrate step then its budgeted step, as the integration job runs them in backend/."""
    return f"cd backend\n{ci_migrate_run()}\n{ci_budgeted_run()}"


def g04_11_integration_script() -> str:
    """The bash block of §4 G04-11 that holds the integration budget line, run as written."""
    budget = ci_env()["INTEGRATION_BUDGET_S"]
    blocks = [
        b for b in bash_blocks(g04_11_section()) if re.search(rf"run_with_budget\.py {budget} ", b)
    ]
    assert len(blocks) == 1, f"§4 G04-11 has {len(blocks)} blocks with a {budget} s budget line"
    return blocks[0]
