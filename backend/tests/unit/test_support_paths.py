"""``tests.support.paths.REPO`` finds the repo root from a mutmut copy too (VR1-S3-01, NFR-072).

mutmut 3 runs the tests inside ``backend/mutants/``, a copy of ``tests/`` and ``src/``. A test
that reads ``docs/`` through ``BACKEND.parent`` then looks in ``backend/docs/`` and the clean run
fails, so the mutation gate scores nothing (G03-11 b). ``REPO`` must be the nearest ancestor that
holds both ``docs/`` and ``backend/``. Negative case first: a tree without such a directory is an
error, never a silent wrong path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.paths import BACKEND, REPO, repo_root

pytestmark = pytest.mark.unit


def _tree(tmp_path: Path, *dirs: str) -> None:
    for d in dirs:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)


def test_a_tree_without_a_repository_root_is_an_error(tmp_path: Path) -> None:
    _tree(tmp_path, "backend/mutants/tests/support")
    with pytest.raises(LookupError):
        repo_root(tmp_path / "backend" / "mutants" / "tests" / "support" / "paths.py")


def test_the_mutmut_copy_resolves_to_the_real_repository(tmp_path: Path) -> None:
    _tree(tmp_path, "docs/domain", "backend/tests/support", "backend/mutants/tests/support")
    copy = tmp_path / "backend" / "mutants" / "tests" / "support" / "paths.py"
    assert repo_root(copy) == tmp_path


def test_the_normal_tree_resolves_to_the_repository(tmp_path: Path) -> None:
    _tree(tmp_path, "docs", "backend/tests/support")
    assert repo_root(tmp_path / "backend" / "tests" / "support" / "paths.py") == tmp_path


def test_the_live_constants_point_at_the_docs_the_doc_sync_tests_read() -> None:
    assert (REPO / "docs" / "domain" / "metric-dictionary.md").is_file()
    assert (REPO / "docs" / "architecture" / "api-sprint-03.md").is_file()
    assert (BACKEND / "src" / "racket").is_dir()
