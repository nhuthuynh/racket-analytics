"""ST-076b (sprint-05 §8: every new domain module joins the nightly mutation list in its own
PR): the corrections fingerprint module is mutated nightly at >= 0.80, and
``mutation_score.py`` accepts a single ``.py`` file as its target (no trailing ``/``).
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR

pytestmark = pytest.mark.unit

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "nightly-quality.yml"
TARGET = "src/racket/matches/scorebook/integrity.py"
TESTS = "tests/unit/matches/test_corrections_integrity.py"


def _fake_mutmut(tmp_path: Path) -> dict[str, str]:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "mutmut"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import shutil, sys\n"
        "if sys.argv[1:] == ['run']:\n"
        f"    shutil.copy('setup.cfg', {str(tmp_path / 'seen.cfg')!r})\n"
    )
    fake.chmod(0o755)
    return {**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}"}


def test_a_single_file_target_and_test_file_are_written_without_a_trailing_slash(
    tmp_path: Path,
) -> None:
    (tmp_path / TARGET).parent.mkdir(parents=True)
    (tmp_path / TARGET).write_text("X = 1\n")
    res = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ci" / "mutation_score.py"), "--project",
         str(tmp_path), "--target", TARGET, "--tests", TESTS, "--tests", "tests/unit/sports/",
         "--out", str(tmp_path / "m.json")],
        capture_output=True, text=True, timeout=60, check=False, env=_fake_mutmut(tmp_path),
    )  # fmt: skip
    assert res.returncode == 1, res.stderr  # the fake writes no stats: never a pass
    seen = (tmp_path / "seen.cfg").read_text()
    assert f"source_paths =\n    {TARGET}\n" in seen
    assert f"pytest_add_cli_args_test_selection =\n    {TESTS}\n    tests/unit/sports/\n" in seen


def test_the_nightly_mutation_job_scores_the_corrections_fingerprint_at_080() -> None:
    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"]["mutation"]["steps"]
    runs = [s for s in steps if f"--target {TARGET} " in " ".join(s.get("run", "").split()) + " "]
    assert len(runs) == 1, f"expected one mutation step for {TARGET}, got {len(runs)}"
    step = runs[0]
    line = next(ln for ln in step["run"].replace("\\\n", " ").splitlines() if "mutation_score" in ln)
    argv = shlex.split(line)
    start = next(i for i, a in enumerate(argv) if a.endswith("mutation_score.py"))
    args = argv[start + 1 :]
    assert args[args.index("--tests") + 1] == TESTS
    assert float(args[args.index("--min-score") + 1]) == 0.80
    assert args[args.index("--out") + 1].startswith("../reports/mutation-")
    assert step.get("if") == "success() || failure()"  # a red step above must not skip it
