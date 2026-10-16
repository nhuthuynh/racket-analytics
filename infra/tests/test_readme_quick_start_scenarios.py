"""Binds tests/features/readme_quick_start.feature (MVP-01; PO MVP goal 2026-10-15).

Runs the real scripts/ci/check_readme_quickstart.py as a subprocess against the real Makefile
and infra/compose.yaml, with either the repository README or a temporary one.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.unit
scenarios("readme_quick_start.feature")

CHECK = SCRIPTS_DIR / "ci" / "check_readme_quickstart.py"


@given(
    parsers.parse('a README whose "Run it locally" section says "{command}"'),
    target_fixture="readme",
)
def readme_with_command(command: str, tmp_path: Path) -> Path:
    f = tmp_path / "README.md"
    f.write_text(f"# x\n\n## Run it locally\n\n```bash\n{command}\n```\n\n## Next\n")
    return f


@given('a README with no "Run it locally" section', target_fixture="readme")
def readme_without_section(tmp_path: Path) -> Path:
    f = tmp_path / "README.md"
    f.write_text("# x\n\nRun `make up`.\n")
    return f


@given("the repository README", target_fixture="readme")
def repo_readme() -> Path:
    return REPO_ROOT / "README.md"


@when("the quick-start check runs", target_fixture="result")
def run_check(readme: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK), "--readme", str(readme), "--repo", str(REPO_ROOT)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


@then(parsers.parse('it fails naming "{text}"'))
def fails_naming(result: subprocess.CompletedProcess[str], text: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert text in result.stdout + result.stderr


@then("it passes")
def passes(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr


def _section() -> str:
    sys.path.insert(0, str(CHECK.parent))
    import check_readme_quickstart as c

    return c.quick_start_section((REPO_ROOT / "README.md").read_text())


@then(parsers.parse('the section names the commands "{a}", "{b}", "{c}", "{d}" and "{e}"'))
def names_five(a: str, b: str, c: str, d: str, e: str) -> None:
    section = _section()
    assert [t for t in (a, b, c, d, e) if t not in section] == []


@then(parsers.parse('the section names the addresses "{a}" and "{b}"'))
def names_two(a: str, b: str) -> None:
    section = _section()
    assert [t for t in (a, b) if t not in section] == []


@then(parsers.parse('the section names the mirror setting "{a}"'))
def names_one(a: str) -> None:
    assert a in _section()
