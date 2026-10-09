"""CI-REDUNTIL-HANG regression: the listed red_until step ends within its bound and fails when a
row waits on a slow object store, instead of running until the job limit.

Root cause (docs/sprints/03/decisions/CI-REDUNTIL-HANG.md): in main run 37961668800 the step
'Rows waiting on a story' ran from 16:52:51 until the 20-minute job limit cancelled it at
17:07:58. Its 88 rows send 174,331,413 bytes to the object store (61 rows upload the 1.72 MB
clip at least once). The store took writes at about 64 KiB/s, as in CI-IT0213-HANG; the
pytest-timeout dumps show the API thread in ``write_chunk`` -> ``upload_part`` -> ``recv_into``.
At that rate each video row needs 40-160 s, so rows sat at the 120 s per-test timeout one
after another, and the report counted a timed-out row as an expected red.

This test runs the step's own pytest options (read from ci.yml) on red_until rows that write
to the real object store through ``slow_object_store`` at ``CI_WRITE_RATE``, then the real
report with the step's row count. Each row would need 64 s for its write.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.support.paths import REPO
from tests.support.slow_store import CI_WRITE_RATE, slow_object_store

pytestmark = pytest.mark.slow

CI = REPO / ".github" / "workflows" / "ci.yml"
REPORT = REPO / "scripts" / "ci" / "red_until_report.py"
STEP_BOUND_S = 120  # done criterion: the step ends in under 2 minutes
ROWS = 2
WRITE = 64 * CI_WRITE_RATE  # 64 s per row at the CI rate

ROW_MODULE = f"""
import os, time
import pytest
from racket.platform.storage import ObjectStore, S3Config

pytestmark = [pytest.mark.red_until(story="ST-999")]


@pytest.mark.parametrize("row", range({ROWS}))
def test_row_waits_on_the_store(row):
    store = ObjectStore(S3Config.from_env())
    key = f"test-own/ci-reduntil-{{os.getpid()}}-{{row}}-{{time.monotonic_ns()}}"
    store.put_bytes(key, b"x" * {WRITE})
    store.delete(key)
    raise AssertionError("RED until ST-999")
"""
INI = """[pytest]
markers =
    red_until(story): written first; fails until the story exists
    nightly: nightly job only
timeout = 120
"""


def _step_run() -> str:
    """The ``run:`` text of the integration job's red_until step, continuation lines joined."""
    text = CI.read_text()
    start = text.index("- name: Rows waiting on a story (red_until")
    end = text.index("\n      - ", start + 1)
    return text[start:end].replace("\\\n", " ")


def _step_pytest_options() -> list[str]:
    """The step's per-row and whole-run bounds, as the step passes them to pytest."""
    line = next(x for x in _step_run().splitlines() if '-m "red_until and not nightly"' in x)
    if "--collect-only" in line:
        raise AssertionError(line)
    tokens = shlex.split(line.split("||")[0])
    keep: list[str] = []
    for i, tok in enumerate(tokens):
        if tok == "-o" and tokens[i + 1].startswith("timeout="):
            keep += ["-o", tokens[i + 1]]
        elif tok.startswith("--session-timeout="):
            keep.append(tok)
    return keep


def test_the_step_options_are_read_from_ci_yml() -> None:
    """Positive control for the parser: it finds the step's pytest line."""
    assert re.search(r'pytest -q -p no:cacheprovider -m "red_until and not nightly"', _step_run())


@pytest.mark.timeout(STEP_BOUND_S + 60)  # this test's own bound: the step's plus the report
def test_rows_waiting_on_a_slow_store_end_the_step_in_time_and_fail_the_report(
    tmp_path: Path,
) -> None:
    (tmp_path / "test_rows.py").write_text(ROW_MODULE)
    (tmp_path / "pytest.ini").write_text(INI)
    xml = tmp_path / "red-until.xml"
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO / "backend" / "src"), env.get("PYTHONPATH", "")])
    with slow_object_store(os.environ["S3_ENDPOINT_URL"]) as slow:
        env["S3_ENDPOINT_URL"] = slow
        started = time.monotonic()
        try:
            subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-c",
                 str(tmp_path / "pytest.ini"), "--rootdir", str(tmp_path),
                 "-m", "red_until and not nightly", *_step_pytest_options(),
                 f"--junitxml={xml}", str(tmp_path / "test_rows.py")],
                cwd=tmp_path, env=env, capture_output=True, text=True, check=False,
                timeout=STEP_BOUND_S + 10,
            )  # fmt: skip
        except subprocess.TimeoutExpired:
            pytest.fail(f"the step's rows were still running after {STEP_BOUND_S + 10} s")
        took = time.monotonic() - started
    report = subprocess.run(
        [sys.executable, str(REPORT), "--junit", str(xml), "--root", str(tmp_path),
         "--expected-rows", str(ROWS)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert took < STEP_BOUND_S, f"the step's rows ran {took:.0f} s on a store at the CI rate"
    assert report.returncode == 1, report.stdout + report.stderr
    assert "timed out" in report.stdout, report.stdout
