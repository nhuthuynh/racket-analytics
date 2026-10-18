"""scripts/ci/warm_hypothesis_constants.py (CI-DOMAIN-BUDGET; NFR-073; ADR 0049).

PR #111 run 39073707402: the warm-up only collects, so a source module that is imported inside a
function (``create_app()`` imports every router, e.g. ``racket.coaching.api``) was parsed by
the xdist workers instead: 26 of 110 constants cache entries were left to the budgeted run.
The warm-up also imports the rest of each source package that collection touched.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest
from domain_budget import BACKEND, REPO_ROOT

pytestmark = pytest.mark.unit
SCRIPT = REPO_ROOT / "scripts" / "ci" / "warm_hypothesis_constants.py"


def _key(path: Path) -> str:
    # Hypothesis's own cache key (constants_ast.constants_from_module), not a security use.
    return hashlib.sha1(path.read_bytes(), usedforsecurity=False).hexdigest()[:16]


def _layout(root: Path) -> dict[str, Path]:
    pkg = root / "src" / "lazypkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("WEEKLY_MINUTES_CAP = 1260\n")
    (pkg / "lazy.py").write_text("GENERATIONS_PER_HOUR = 31337\n")
    (pkg / "broken.py").write_text('raise RuntimeError("needs a runtime context")\n')
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "import lazypkg\n\n\n"
        "def test_imports_at_run_time():\n"
        "    from lazypkg import lazy\n\n"
        "    assert lazy.GENERATIONS_PER_HOUR\n"
    )
    return {"init": pkg / "__init__.py", "lazy": pkg / "lazy.py", "test": tests / "test_sample.py"}


def _warm(root: Path) -> tuple[subprocess.CompletedProcess[str], Path]:
    storage = root / "hypothesis"
    env = {"HYPOTHESIS_STORAGE_DIRECTORY": str(storage), "PYTHONPATH": str(root / "src")}
    cmd = ["uv", "run", "--no-sync", "--project", str(BACKEND), "python", str(SCRIPT), "tests"]
    res = subprocess.run(
        cmd, cwd=root, env={**os.environ, **env}, capture_output=True, text=True, timeout=300
    )
    return res, storage / "constants"


def test_a_source_module_imported_only_inside_a_function_is_warmed(tmp_path: Path) -> None:
    files = _layout(tmp_path)
    res, cache = _warm(tmp_path)
    assert res.returncode == 0, res.stdout[-2000:] + res.stderr[-2000:]
    entries = {p.name for p in cache.glob("*")}
    assert _key(files["lazy"]) in entries, (sorted(entries), res.stdout[-1000:])
    assert _key(files["init"]) in entries
    # A module that cannot be imported outside its runtime does not stop the warm-up.
    assert "warm:" in res.stdout


def test_the_warm_up_also_builds_the_unicode_tables(tmp_path: Path) -> None:
    """PR #111 run 39100944732: without ``charmap.json.gz`` each xdist worker builds it on its
    first ``st.text()`` (domain suite 10 s vs 8 s on main); main's warm-up drew one text example."""
    _layout(tmp_path)
    res, cache = _warm(tmp_path)
    assert res.returncode == 0, res.stdout[-2000:] + res.stderr[-2000:]
    assert list(cache.parent.glob("unicode_data/*/charmap.json.gz")), res.stdout[-1000:]
    assert list(cache.parent.glob("unicode_data/*/codec-*utf-8.json.gz")), res.stdout[-1000:]
