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


def test_measure_of_an_empty_diff_is_zero() -> None:
    assert size.measure("") == size.Size(counted=0, excluded=0)
