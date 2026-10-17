"""C4-RED unit tests: commit classification and the red-first verdict (no git, no I/O)."""

from __future__ import annotations

import sys

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR

sys.path.insert(0, str(SCRIPTS_DIR / "ci"))
import check_red_first as rf

pytestmark = pytest.mark.unit
B, W = "backend/src/a.py", "web/src/b.ts"


@pytest.mark.parametrize(
    ("paths", "kind"),
    [  # negative first: any production path makes a code commit
        ((B,), "CODE"), ((W,), "CODE"), (("backend/tests/t.py", B), "CODE"), (("d.md", W), "CODE"),
        (("backend/tests/unit/t.py",), "TEST_ONLY"), (("web/tests/unit/a.test.tsx",), "TEST_ONLY"),
        (("web/e2e/p.spec.ts",), "TEST_ONLY"), (("tests/features/r.feature",), "TEST_ONLY"),
        (("infra/tests/t.py", "docs/d.md"), "TEST_ONLY"), (("fixtures/gold/m.json",), "TEST_ONLY"),
        ((), "OTHER"), (("docs/n.md",), "OTHER"), (("scripts/ci/x.py",), "OTHER"),
        (("backend/srcx/a.py",), "OTHER"), (("web/src.md",), "OTHER"),
    ],
)  # fmt: skip
def test_classify(paths: tuple[str, ...], kind: str) -> None:
    assert rf.classify(paths) is rf.Kind[kind]


def test_name_status_keeps_added_changed_and_renamed_paths_not_deletions() -> None:
    out = (
        f"A\t{B}\nM\t{W}\nD\tbackend/src/gone.py\nR100\tbackend/src/o.py\tlib/n.py\nT\tweb/src/l\n"
    )
    assert rf.changed_paths(out) == (B, W, "backend/src/o.py", "lib/n.py", "web/src/l")


@pytest.mark.parametrize(
    ("body", "red"),
    [  # negative first
        ("", False), ("red: lower case", False), ("Red:", False), ("Red:   ", False),
        ("  Red: indented is a quote", False), ("see the Red: line", False),
        ("Red: pytest -> 1 failed", True), ("why\n\nRed: vitest -> 2 failed\nCo-Author: x", True),
    ],
)  # fmt: skip
def test_red_line(body: str, red: bool) -> None:
    assert rf.has_red_line(body) is red


def c(sha: str, *paths: str, body: str = "") -> object:
    return rf.Commit(sha=sha, subject=f"s {sha}", body=body, paths=paths)


@pytest.mark.parametrize(
    ("commits", "flagged"),
    [  # negative first
        ([c("c1", B, "backend/tests/unit/t.py")], ["c1"]),  # code and tests together
        ([c("c1", W), c("t1", "web/tests/unit/a.test.ts")], ["c1"]),  # a later test is late
        ([c("c1", W), c("c2", B)], ["c1", "c2"]),  # each one is named
        ([c("c1", B, body="Red: 1 failed"), c("c2", W)], ["c2"]),  # Red: covers its own
        ([c("t1", "backend/tests/t.py"), c("c1", B), c("d1", "docs/a.md"), c("c2", B)], []),
        ([c("d1", "docs/a.md"), c("t1", "tests/features/a.feature")], []),
    ],
)  # fmt: skip
def test_findings(commits: list[object], flagged: list[str]) -> None:
    assert [f.sha for f in rf.findings(commits)] == flagged


def test_red_first_runs_in_pr_policy_which_ci_gate_requires() -> None:
    jobs = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())["jobs"]
    step = {s.get("name"): s for s in jobs["pr-policy"]["steps"]}["Red first (R3-IN-1, C4-RED)"]
    assert (
        step["run"] == 'python3 scripts/ci/check_red_first.py --base "origin/$BASE_REF" --head HEAD'
    )
    assert step["env"]["BASE_REF"] == "${{ github.base_ref }}"
    assert "pr-policy" in jobs["ci-gate"]["needs"]
