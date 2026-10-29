"""MVP-01: unit tests for scripts/ci/check_readme_quickstart.py (README 'Run it locally')."""

from __future__ import annotations

import subprocess
import sys

import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR

sys.path.insert(0, str(SCRIPTS_DIR / "ci"))
import check_readme_quickstart as c

pytestmark = pytest.mark.unit

MAKEFILE = """\
.PHONY: up
up: $(ENV_FILE) ## Build and start
\t$(COMPOSE) up
down: ## Stop and delete volumes
\t$(COMPOSE) down -v
$(ENV_FILE):
\tcp a b
internal:
\techo no help
"""
COMPOSE = "image: ${DOCKERHUB_REGISTRY:-docker.io}/library/postgres:16\n"


def readme(body: str) -> str:
    return f"# app\n\n## Run it locally\n\n{body}\n\n## Docs\n\nRun `make elsewhere`.\n"


def test_a_target_without_help_text_is_not_a_documented_target() -> None:
    assert c.makefile_targets(MAKEFILE) == {"up", "down"}


def test_missing_section_is_the_only_problem_reported() -> None:
    assert c.problems("# app\n\n`make up`\n", MAKEFILE, COMPOSE) == [
        "README has no '## Run it locally' section"
    ]


def test_unknown_make_target_in_the_section_is_reported() -> None:
    assert c.problems(readme("```bash\nmake launch\n```"), MAKEFILE, COMPOSE) == [
        "README names `make launch` but the Makefile has no documented `launch` target"
    ]


def test_unknown_compose_variable_in_the_section_is_reported() -> None:
    text = readme("`REGISTRY_MIRROR=mirror.gcr.io make up`")
    assert c.problems(text, MAKEFILE, COMPOSE) == [
        "README sets `REGISTRY_MIRROR` but infra/compose.yaml does not read it"
    ]


def test_targets_and_variables_outside_the_section_are_ignored() -> None:
    text = readme("```bash\nDOCKERHUB_REGISTRY=mirror.gcr.io make up\nmake down\n```")
    assert c.problems(text, MAKEFILE, COMPOSE) == []


def test_make_targets_named_reads_commands_in_code_only() -> None:
    section = "Use make up to start.\n\n`make up`, `make  down`\n\n```\n$ make ps logs\n```\n"
    assert c.make_targets_named(section) == ["up", "down", "ps", "logs"]


def test_section_stops_at_the_next_heading_of_the_same_level() -> None:
    text = readme("### Troubleshooting\n\n`make down`")
    section = c.quick_start_section(text)
    assert "Troubleshooting" in section
    assert "make elsewhere" not in section


# ST-066: the "Try the prototype" walkthrough (QD §7; goal G04-06).

WALKTHROUGH = """\
### Try the prototype

1. `make up`, then `make demo`.
2. Open the stats URL it prints (`https://localhost:3000/matches/<id>/stats`).
3. Open `https://localhost:3000/plan`.
4. Read a drill's **Why** and press **Show me**.
5. Press **Mark done** on a session.
6. Press **Not for me** on a drill.
7. `make down`.
"""


def test_a_walkthrough_missing_a_step_names_that_step() -> None:
    section = c.quick_start_section(readme(WALKTHROUGH.replace("**Not for me**", "Swap")))
    assert c.walkthrough_problems(section) == [
        "the 'Try the prototype' walkthrough does not name step: Not for me (`Not for me`)"
    ]


def test_a_section_without_the_walkthrough_is_reported_once() -> None:
    assert c.walkthrough_problems(c.quick_start_section(readme("`make up`"))) == [
        "README 'Run it locally' has no '### Try the prototype' walkthrough"
    ]


def test_a_step_out_of_order_is_reported() -> None:
    swapped = WALKTHROUGH.replace("5. Press **Mark done** on a session.\n", "").replace(
        "2. Open", "2. Press **Mark done** on a session. Open"
    )
    assert c.walkthrough_problems(c.quick_start_section(readme(swapped))) == [
        "the 'Try the prototype' walkthrough names Mark done (`Mark done`) before Show me"
    ]


def test_a_complete_walkthrough_has_no_problems() -> None:
    assert c.walkthrough_problems(c.quick_start_section(readme(WALKTHROUGH))) == []


def test_the_walkthrough_stops_at_the_next_subsection() -> None:
    text = readme(WALKTHROUGH.replace("7. `make down`.", "### Later\n\n`make down`"))
    assert c.walkthrough_problems(c.quick_start_section(text)) == [
        "the 'Try the prototype' walkthrough does not name step: make down (`make down`)"
    ]


def test_main_reports_walkthrough_problems_with_rc_1(tmp_path, capsys) -> None:
    (tmp_path / "Makefile").write_text(MAKEFILE)
    (tmp_path / "infra").mkdir()
    (tmp_path / "infra" / "compose.yaml").write_text(COMPOSE)
    (tmp_path / "README.md").write_text(readme("`make up`"))
    assert c.main(["--repo", str(tmp_path)]) == 1
    assert "no '### Try the prototype' walkthrough" in capsys.readouterr().out


@pytest.mark.integration
def test_the_repository_readme_passes_the_checker_with_its_walkthrough() -> None:
    res = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ci" / "check_readme_quickstart.py"), "--repo", "."],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert (res.returncode, res.stdout) == (0, "readme-quickstart: ok\n"), res.stdout + res.stderr
    section = c.quick_start_section((REPO_ROOT / "README.md").read_text())
    assert c.walkthrough_problems(section) == []
