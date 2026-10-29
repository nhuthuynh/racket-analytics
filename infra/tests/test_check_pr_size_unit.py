"""CI-SIZE-PROD-ONLY unit tests: which paths count toward the PR size limit (no git, no I/O).

PO decision 2026-10-28 (ADR 0053): the 400-line limit counts production code only; tests,
docs, lockfiles and fixtures are excluded but still reported.
"""

from __future__ import annotations

import sys

import pytest
from conftest import SCRIPTS_DIR

sys.path.insert(0, str(SCRIPTS_DIR / "ci"))
import check_pr_size as size

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "path",
    [  # negative first: production code must still count, wherever it lives
        "backend/src/app/scoring.py",
        "backend/src/app/testing_helpers.py",
        "web/src/app/page.tsx",
        "web/src/lib/contest.ts",
        "scripts/ci/check_pr_size.py",
        ".github/workflows/ci.yml",
        "infra/compose.yaml",
        "Makefile",
        "backend/pyproject.toml",
    ],
)
def test_production_code_counts(path: str) -> None:
    assert not size.is_excluded(path)


@pytest.mark.parametrize(
    "path",
    [
        "backend/tests/unit/test_scoring.py",
        "backend/tests/conftest.py",
        "web/tests/unit/score.test.tsx",
        "web/src/lib/contest.test.ts",
        "web/src/app/page.spec.ts",
        "infra/tests/test_ci_scripts.py",
        "infra/conftest.py",
        "e2e/journey.ts",
        "web/e2e/sprint-01/resumable-upload.spec.ts",
        "tests/features/pr_policy.feature",
        "docs/process/working-agreement.md",
        "docs/sprints/04/status.json",
        "README.md",
        ".claude/agents/sre-devops-engineer.md",
        "backend/uv.lock",
        "web/pnpm-lock.yaml",
        "package-lock.json",
        "fixtures/clips/synthetic-60s/manifest.json",
        "web/src/__snapshots__/a.snap",
    ],
)
def test_tests_docs_lockfiles_and_fixtures_are_excluded(path: str) -> None:
    assert size.is_excluded(path)


def test_measure_splits_counted_and_excluded_lines_and_skips_binaries() -> None:
    numstat = "\n".join(
        [
            "10\t5\tbackend/src/a.py",
            "300\t0\tbackend/tests/unit/test_a.py",
            "7\t3\tdocs/notes.md",
            "-\t-\tfixtures/clip.mp4",
            "-\t-\tweb/src/logo.png",
        ]
    )
    assert size.measure(numstat) == size.Size(counted=15, excluded=310)


@pytest.mark.parametrize(
    ("record", "counted", "excluded"),
    [  # PE-SIZEPROD-R1-01: a rename is classified by its destination, never the "a => b" text
        ("450\t450\ttests/helper.py => app/service.py", 900, 0),
        ("450\t450\t{tests => app}/helper.py", 900, 0),
        ("3\t1\tbackend/{tests/unit => src/app}/x.py", 4, 0),
        ("5\t5\tbackend/src/{app => }/y.py", 10, 0),
        ("8\t2\tbackend/src/app.py => docs/app.md", 0, 10),
        ("8\t2\t{backend/src => backend/tests}/a.py", 0, 10),
    ],
)
def test_measure_classifies_a_rename_by_its_destination(
    record: str, counted: int, excluded: int
) -> None:
    assert size.measure(record) == size.Size(counted=counted, excluded=excluded)


@pytest.mark.parametrize(
    ("record", "path"),
    [
        ("tests/helper.py => app/service.py", "app/service.py"),
        ("{tests => app}/helper.py", "app/helper.py"),
        ("backend/{tests/unit => src/app}/x.py", "backend/src/app/x.py"),
        ("backend/src/{app => }/y.py", "backend/src/y.py"),
        ("backend/src/{ => app}/y.py", "backend/src/app/y.py"),
        ("backend/src/a.py", "backend/src/a.py"),
    ],
)
def test_destination_of_a_numstat_path(record: str, path: str) -> None:
    assert size.destination(record) == path


def test_measure_of_an_empty_diff_is_zero() -> None:
    assert size.measure("") == size.Size(counted=0, excluded=0)
