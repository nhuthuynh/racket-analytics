"""Support for the CI-INTEG-BUDGET tests: a fresh Postgres cluster, the integration job's migrate
step as ci.yml declares it, and ``parallel_migrate.py`` run with the backend's interpreter.

Real Postgres 16 from ``scripts/dev-postgres.sh`` (no mocks, never SQLite). Needs ``uv``; a
missing ``uv`` fails, it never skips.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
BACKEND = REPO_ROOT / "backend"
HELPER = Path(__file__).with_name("parallel_migrate.py")
BUDGET_MARK = "$INTEGRATION_BUDGET_S"
MIGRATE_MODULE = re.compile(r"\bpython3? -m (racket\.[\w.]+migrate)\b")


def integration_steps() -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = yaml.safe_load(CI.read_text())["jobs"]["integration"]["steps"]
    return steps


def step_index(steps: list[dict[str, Any]], needle: str | re.Pattern[str]) -> int:
    for i, s in enumerate(steps):
        run = s.get("run", "")
        if needle.search(run) if isinstance(needle, re.Pattern) else needle in run:
            return i
    return -1


def migrate_step() -> dict[str, Any]:
    steps = integration_steps()
    i = step_index(steps, MIGRATE_MODULE)
    assert i >= 0, "the integration job has no step that migrates the base database"
    return steps[i]


def migrate_module() -> str:
    m = MIGRATE_MODULE.search(migrate_step()["run"])
    assert m
    return m.group(1)


@contextmanager
def fresh_cluster(state: Path) -> Iterator[str]:
    """A new Postgres cluster (no roles but its owner); yields its DATABASE_URL."""
    env = {**os.environ, "RA_DEV_STATE": str(state)}
    script = str(SCRIPTS_DIR / "dev-postgres.sh")
    start = subprocess.run(["bash", script, "start"], env=env, capture_output=True, text=True,
                           timeout=120, check=False)  # fmt: skip
    assert start.returncode == 0, start.stderr
    m = re.search(r"^export DATABASE_URL=(\S+)$", start.stdout, re.MULTILINE)
    assert m, start.stdout
    try:
        yield m.group(1).strip("'\"")
    finally:
        subprocess.run(["bash", script, "stop"], env=env, capture_output=True, timeout=120,
                       check=False)  # fmt: skip


def collides_on(role: str, failure: str) -> bool:
    """Both ways Postgres reports two CREATE ROLE of one name: the unique index, or the catalog
    check when the other transaction committed first."""
    return "pg_authid_rolname_index" in failure or f'role "{role}" already exists' in failure


def unique_role() -> str:
    return f"ra_it_cluster_{uuid.uuid4().hex[:8]}"


def run_helper(*args: str, timeout: float = 600) -> dict[str, Any]:
    if shutil.which("uv") is None:
        pytest.fail("uv not on PATH (CI: pip install uv) - fails closed, no skip")
    env = {**os.environ, "APP_ENV": "test"}
    env.pop("VIRTUAL_ENV", None)  # the infra venv must not leak into the backend project
    res = subprocess.run(["uv", "run", "--locked", "python", str(HELPER), *args], cwd=BACKEND,
                         env=env, capture_output=True, text=True, timeout=timeout,
                         check=False)  # fmt: skip
    assert res.returncode == 0, (res.stdout + res.stderr)[-3000:]
    out: dict[str, Any] = json.loads(res.stdout.strip().splitlines()[-1])
    return out
