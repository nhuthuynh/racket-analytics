"""C4-RED unit tests: commit classification and the red-first verdict (no git, no I/O).

The ubiquitous language: a *code commit* adds or changes production code (backend/src, web/src);
a *test-only commit* changes tests and no production code; a *red step* is a `Red:` body line
or an earlier test-only commit in the same pull request.
"""

from __future__ import annotations

import importlib.util
import sys

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit

_spec = importlib.util.spec_from_file_location(
    "check_red_first", SCRIPTS_DIR / "ci" / "check_red_first.py"
)
assert _spec
assert _spec.loader
rf = importlib.util.module_from_spec(_spec)
sys.modules["check_red_first"] = rf
_spec.loader.exec_module(rf)


def commit(sha: str, *paths: str, body: str = "") -> object:
    return rf.Commit(sha=sha, subject=f"subject {sha}", body=body, paths=tuple(paths))


# ------------------------------------------------------------------ classification (negative first)
@pytest.mark.parametrize(
    "paths",
    [
        ("backend/src/racket/rule.py",),
        ("web/src/app/page.tsx",),
        ("backend/tests/unit/test_rule.py", "backend/src/racket/rule.py"),
        ("docs/x.md", "web/src/lib/a.ts"),
    ],
)
def test_any_production_path_makes_a_code_commit(paths: tuple[str, ...]) -> None:
    assert rf.classify(paths) is rf.Kind.CODE


@pytest.mark.parametrize(
    "paths",
    [
        ("backend/tests/unit/test_rule.py",),
        ("web/tests/unit/a.test.tsx",),
        ("web/e2e/sprint-04/plan.spec.ts",),
        ("tests/features/red_first_check.feature",),
        ("infra/tests/test_x.py", "docs/sprints/04/decisions/C4-RED.md"),
        ("fixtures/gold/m.json",),
    ],
)
def test_tests_without_production_code_make_a_test_only_commit(paths: tuple[str, ...]) -> None:
    assert rf.classify(paths) is rf.Kind.TEST_ONLY


@pytest.mark.parametrize(
    "paths",
    [(), ("docs/notes.md",), ("scripts/ci/x.py",), ("backend/srcx/a.py",), ("web/src.md",)],
)
def test_no_tests_and_no_production_code_is_other(paths: tuple[str, ...]) -> None:
    assert rf.classify(paths) is rf.Kind.OTHER


def test_name_status_keeps_added_changed_and_renamed_paths_not_deletions() -> None:
    out = "\n".join(
        [
            "A\tbackend/src/a.py",
            "M\tweb/src/b.ts",
            "D\tbackend/src/gone.py",
            "R100\tbackend/src/old.py\tlib/new.py",
            "T\tweb/src/link",
            "",
        ]
    )
    assert rf.changed_paths(out) == (
        "backend/src/a.py",
        "web/src/b.ts",
        "backend/src/old.py",
        "lib/new.py",
        "web/src/link",
    )


# ------------------------------------------------------------------ Red: line (negative first)
@pytest.mark.parametrize(
    "body",
    ["", "red: lower case", "Red:", "Red:   ", "  Red: indented is a quote", "see the Red: line"],
)
def test_body_without_a_red_line(body: str) -> None:
    assert not rf.has_red_line(body)


@pytest.mark.parametrize(
    "body",
    ["Red: pytest -> 1 failed", "why\n\nRed: vitest -> 2 failed\nCo-Authored-By: x"],
)
def test_body_with_a_red_line(body: str) -> None:
    assert rf.has_red_line(body)


# ------------------------------------------------------------------ verdict (negative first)
def test_code_commit_without_red_step_is_a_finding() -> None:
    found = rf.findings([commit("c1", "backend/src/a.py", "backend/tests/unit/test_a.py")])
    assert [(f.sha, f.code_paths) for f in found] == [("c1", ("backend/src/a.py",))]


def test_later_test_only_commit_does_not_excuse_an_earlier_code_commit() -> None:
    found = rf.findings([commit("c1", "web/src/a.ts"), commit("t1", "web/tests/unit/a.test.ts")])
    assert [f.sha for f in found] == ["c1"]


def test_each_code_commit_without_red_step_is_named() -> None:
    found = rf.findings([commit("c1", "web/src/a.ts"), commit("c2", "backend/src/b.py")])
    assert [f.sha for f in found] == ["c1", "c2"]


def test_earlier_test_only_commit_is_the_red_step_for_every_later_code_commit() -> None:
    commits = [
        commit("t1", "backend/tests/unit/test_a.py"),
        commit("c1", "backend/src/a.py"),
        commit("d1", "docs/a.md"),
        commit("c2", "backend/src/a.py"),
    ]
    assert rf.findings(commits) == []


def test_red_line_is_the_red_step_of_its_own_commit_only() -> None:
    commits = [commit("c1", "backend/src/a.py", body="Red: 1 failed"), commit("c2", "web/src/b.ts")]
    assert [f.sha for f in rf.findings(commits)] == ["c2"]


def test_docs_and_test_only_commits_have_no_findings() -> None:
    commits = [commit("d1", "docs/a.md"), commit("t1", "tests/features/a.feature")]
    assert rf.findings(commits) == []


# ------------------------------------------------------------------ ci.yml wiring
def test_red_first_runs_in_pr_policy_which_ci_gate_requires() -> None:
    import yaml
    from conftest import REPO_ROOT

    jobs = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())["jobs"]
    steps = {s.get("name"): s for s in jobs["pr-policy"]["steps"]}
    step = steps["Red first (R3-IN-1, C4-RED)"]
    assert step["run"] == (
        'python3 scripts/ci/check_red_first.py --base "origin/$BASE_REF" --head HEAD'
    )
    assert step["env"]["BASE_REF"] == "${{ github.base_ref }}"
    assert "pr-policy" in jobs["ci-gate"]["needs"]
