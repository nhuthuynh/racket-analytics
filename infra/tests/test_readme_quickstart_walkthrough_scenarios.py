"""Binds tests/features/readme_quickstart.feature (ST-066; QD §7; goal G04-06).

Runs the real scripts/ci/check_readme_quickstart.py as a subprocess against the real Makefile
and infra/compose.yaml, with either the repository README or a temporary one.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.unit
scenarios("readme_quickstart.feature")

CHECK = SCRIPTS_DIR / "ci" / "check_readme_quickstart.py"
FULL_WALKTHROUGH = """\
### Try the prototype

1. `make up`, then `make demo`.
2. Open the stats URL it prints (`https://localhost:3000/matches/<id>/stats`).
3. Open `https://localhost:3000/plan`.
4. Read a drill's **Why** and press **Show me**.
5. Press **Mark done** on a session.
6. Press **Not for me** on a drill.
7. `make down`.
"""


def _readme(tmp_path: Path, section_body: str) -> Path:
    f = tmp_path / "README.md"
    f.write_text(f"# x\n\n## Run it locally\n\n```bash\nmake up\n```\n\n{section_body}\n## Next\n")
    return f


@given(
    parsers.parse('a README whose "Try the prototype" walkthrough leaves out "{step}"'),
    target_fixture="readme",
)
def readme_without_step(step: str, tmp_path: Path) -> Path:
    body = "\n".join(line for line in FULL_WALKTHROUGH.splitlines() if step not in line)
    return _readme(tmp_path, body + "\n")


@given(
    'a README whose "Run it locally" section has no "Try the prototype" walkthrough',
    target_fixture="readme",
)
def readme_without_walkthrough(tmp_path: Path) -> Path:
    return _readme(tmp_path, "Then open https://localhost:3000.\n")


@given("the repository README", target_fixture="readme")
def repo_readme() -> Path:
    return REPO_ROOT / "README.md"


@when("the quick-start check runs on it", target_fixture="result")
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
    assert text in result.stdout, result.stdout + result.stderr


@then("it passes")
def passes(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert "readme-quickstart: ok" in result.stdout


@then(parsers.re(r"the walkthrough names, in order, (?P<items>.+)"))
def walkthrough_names_in_order(items: str) -> None:
    sys.path.insert(0, str(CHECK.parent))
    import check_readme_quickstart as c

    section = c.quick_start_section((REPO_ROOT / "README.md").read_text())
    walkthrough = c.walkthrough_section(section)
    wanted = re.findall(r'"([^"]+)"', items)
    assert [t for t in wanted if t not in walkthrough] == []
    at = [walkthrough.index(t) for t in wanted]
    assert at == sorted(at), dict(zip(wanted, at, strict=True))
