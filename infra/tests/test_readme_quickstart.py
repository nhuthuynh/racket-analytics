"""MVP-01: unit tests for scripts/ci/check_readme_quickstart.py (README 'Run it locally')."""

from __future__ import annotations

import sys

import pytest
from conftest import SCRIPTS_DIR

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
