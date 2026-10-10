"""PE-R3S3-04: ADR 0039's per-ticket plan names every commit of a range exactly once.

Unit tests drive the pure counting; integration tests run the CLI on a real git repository.
Negative cases first.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from adr_plan_repo import SCRIPT, adr_naming, make_repo, run_check


def _module():  # loaded from scripts/ci, not a package
    spec = importlib.util.spec_from_file_location("adr_commit_plan", SCRIPT)
    assert spec is not None, f"missing {SCRIPT}"
    assert spec.loader is not None, f"missing {SCRIPT}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


A = "75338b9" + "0" * 33
B = "ccc2fe9" + "1" * 33
C = "783cfd2" + "2" * 33


# ---------------------------------------------------------------- unit: negative cases first
@pytest.mark.unit
def test_a_commit_the_text_never_names_is_missing() -> None:
    problems = _module().plan_problems([A, B, C], "| `75338b9` | | `ccc2fe9` |")
    assert problems == [f"{C[:7]}: missing (named 0 times)"]


@pytest.mark.unit
def test_a_commit_named_twice_is_a_problem() -> None:
    problems = _module().plan_problems([A, B], "`75338b9` `ccc2fe9` and again 75338b9")
    assert problems == [f"{A[:7]}: named 2 times"]


@pytest.mark.unit
def test_a_longer_form_of_the_same_sha_counts_as_naming_it() -> None:
    problems = _module().plan_problems([A], f"`75338b9` then {A}")
    assert problems == [f"{A[:7]}: named 2 times"]


@pytest.mark.unit
def test_a_hex_word_that_only_starts_like_the_sha_does_not_count() -> None:
    # "75338b9f" is not a prefix of A (A continues with "0"), so it is another commit
    problems = _module().plan_problems([A], "75338b9f")
    assert problems == [f"{A[:7]}: missing (named 0 times)"]


@pytest.mark.unit
def test_a_sha_glued_into_a_longer_word_does_not_count() -> None:
    problems = _module().plan_problems([A], "x75338b9 75338b9y")
    assert problems == [f"{A[:7]}: missing (named 0 times)"]


@pytest.mark.unit
def test_an_empty_range_is_refused() -> None:
    with pytest.raises(ValueError, match="no commits"):
        _module().plan_problems([], "`75338b9`")


@pytest.mark.unit
def test_each_commit_named_once_has_no_problem() -> None:
    assert _module().plan_problems([A, B, C], "`75338b9`, ccc2fe9 and 783cfd2.") == []


# ---------------------------------------------------------------- integration: the CLI on real git
@pytest.mark.integration
def test_cli_names_the_commit_with_no_row(tmp_path: Path) -> None:
    repo, shas = make_repo(tmp_path)
    out = run_check(repo, adr_naming(tmp_path / "adr.md", shas[:2]), "main..sprint")
    assert out.returncode == 1, out.stdout + out.stderr
    assert f"{shas[2][:7]}: missing (named 0 times)" in out.stdout


@pytest.mark.integration
def test_cli_names_the_commit_with_two_rows(tmp_path: Path) -> None:
    repo, shas = make_repo(tmp_path)
    out = run_check(repo, adr_naming(tmp_path / "adr.md", [*shas, shas[0]]), "main..sprint")
    assert out.returncode == 1, out.stdout + out.stderr
    assert f"{shas[0][:7]}: named 2 times" in out.stdout


@pytest.mark.integration
def test_cli_refuses_a_range_git_cannot_read(tmp_path: Path) -> None:
    repo, shas = make_repo(tmp_path)
    out = run_check(repo, adr_naming(tmp_path / "adr.md", shas), "main..no-such-branch")
    assert out.returncode == 2, out.stdout + out.stderr
    assert out.stderr.startswith("adr-plan: "), out.stderr


@pytest.mark.integration
def test_cli_refuses_a_missing_adr(tmp_path: Path) -> None:
    repo, _ = make_repo(tmp_path)
    out = run_check(repo, tmp_path / "absent.md", "main..sprint")
    assert out.returncode == 2, out.stdout + out.stderr
    assert out.stderr.startswith("adr-plan: "), out.stderr


@pytest.mark.integration
def test_cli_refuses_an_empty_range(tmp_path: Path) -> None:
    repo, shas = make_repo(tmp_path)
    out = run_check(repo, adr_naming(tmp_path / "adr.md", shas), "sprint..main")
    assert out.returncode == 2, out.stdout + out.stderr
    assert out.stderr.startswith("adr-plan: "), out.stderr


@pytest.mark.integration
def test_cli_passes_when_every_commit_is_named_once(tmp_path: Path) -> None:
    repo, shas = make_repo(tmp_path)
    out = run_check(repo, adr_naming(tmp_path / "adr.md", shas), "main..sprint")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "3 commits in main..sprint, each named once" in out.stdout
