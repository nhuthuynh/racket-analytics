"""CI-DOC-CHECK unit tests (PRC-3.1-3.4): scripts/ci/check_docs.py run as a process, as CI runs
it, on the planted-break fixture set (doc_check_repo.py), one break per rule, negative first; and
the ci.yml wiring (a draft-skipped `doc-check` job that `ci-gate` needs)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT
from doc_check_repo import AGENT_OK, commit, flows_text, make_repo, run_check, write
from workflow_if import DRAFT_PR, PUSH, READY_PR, evaluate

pytestmark = pytest.mark.unit

CI = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())
AGENT = ".claude/agents/sre-devops-engineer.md"


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    return root, make_repo(root)


def check(root: Path, base: str) -> tuple[int, str]:
    proc = run_check(root, "--base", base, "--head", "HEAD")
    return proc.returncode, proc.stdout + proc.stderr


# ------------------------------------------------------------------ PRC-3.1 repo paths
def test_dangling_path_in_a_planted_markdown_file_fails(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, "docs/planted.md", "# Planted\n\nRun `scripts/ci/missing_tool.py` first.\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert "FAIL path: docs/planted.md:3: scripts/ci/missing_tool.py does not exist" in out


def test_dangling_relative_link_fails(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, "docs/planted.md", "See [the plan](sprints/sprint-99.md#goal).\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert "FAIL path: docs/planted.md:1: sprints/sprint-99.md does not exist" in out


def test_existing_paths_pass(repo: tuple[Path, str]) -> None:
    root, base = repo
    text = (
        "Root path `scripts/ci/tool.py:3`, a node id `backend/tests/unit/test_x.py::test_x`,\n"
        "a subproject-relative path `tests/unit/test_x.py`, a directory `scripts/ci/`,\n"
        "a git-ignored path `infra/.env`, a link [plan](sprints/sprint-05.md#top),\n"
        "a URL [x](https://example.invalid/a), placeholders `docs/sprints/<nn>/status.json`,\n"
        "`docs/decisions/0057-*.md` and `scripts/ci/...`, prose `and/or` and `docs/x y`.\n"
    )
    write(root, "docs/planted.md", text)
    commit(root)
    rc, out = check(root, base)
    assert rc == 0, out
    assert "0 problem(s)" in out


def test_planned_marker_allows_a_path_that_does_not_exist_yet(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, "docs/planted.md", "New gate `scripts/ci/check_atomic_breakdown.py` (planned).\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 0, out


def test_only_lines_added_by_the_change_are_path_checked(repo: tuple[Path, str]) -> None:
    root, base = repo
    plan = root / "docs/sprints/sprint-05.md"
    plan.write_text(plan.read_text() + "\nNew line: `scripts/ci/tool.py`.\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 0, out
    assert "gone.py" not in out


def test_unchanged_files_are_not_checked(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, "README.txt", "not markdown `scripts/ci/missing.py`\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 0, out
    assert "0 file(s)" in out


# ------------------------------------------------------------------ PRC-3.2 [ASB/<ID>] citations
@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Hooks run [ASB/ANT-03].", "FAIL citation: docs/planted.md:1: ASB/ANT-03 is Not confirmed"),
        ("Flow [ASB/AGL-20], see.", "FAIL citation: docs/planted.md:1: ASB/AGL-20 is Unverified"),
        ("Ghost [ASB/ANT-99].", "FAIL citation: docs/planted.md:1: ASB/ANT-99 is not in the register"),
        ("Pair [ASB/ANT-01, ASB/ANT-03].", "FAIL citation: docs/planted.md:1: ASB/ANT-03"),
        ("Late (unverified) [ASB/ANT-03].", "FAIL citation: docs/planted.md:1: ASB/ANT-03"),
    ],
)
def test_unconfirmed_citation_without_marker_fails(
    repo: tuple[Path, str], line: str, expected: str
) -> None:
    root, base = repo
    write(root, "docs/planted.md", line + "\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert expected in out


@pytest.mark.parametrize(
    "line",
    [
        "Subagents [ASB/ANT-01].",
        "Hooks [ASB/ANT-03] (unverified).",
        "Both [ASB/ANT-01], [ASB/AGL-20] (unverified).",
        "Placeholder `[ASB/<ID>]` and [ASB/...] are not citations.",
    ],
)
def test_confirmed_or_marked_citation_passes(repo: tuple[Path, str], line: str) -> None:
    root, base = repo
    write(root, "docs/planted.md", line + "\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 0, out


def test_missing_register_is_a_failure_not_a_pass(repo: tuple[Path, str]) -> None:
    root, base = repo
    (root / "docs/research/agentic-sdlc-best-practices.md").unlink()
    write(root, "docs/planted.md", "Subagents [ASB/ANT-01].\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert "FAIL citation: register docs/research/agentic-sdlc-best-practices.md not found" in out


# ------------------------------------------------------------------ PRC-3.3 agent front matter
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (AGENT_OK.replace("tools: Read, Grep, Bash\n", ""), "lacks tools"),
        (AGENT_OK.replace("name: sre-devops-engineer\n", ""), "lacks name"),
        (AGENT_OK.replace("description: SRE / DevOps Engineer.\n", "description:\n"), "lacks description"),
        (AGENT_OK.replace("tools: Read", "tools: [Read"), "does not parse"),
        (AGENT_OK.split("---\n", 2)[2], "has no front matter"),
        (AGENT_OK.replace("model: sonnet\n---", "model: sonnet\n"), "has no front matter"),
        ("---\n- a list\n---\nbody\n", "is not a mapping"),
    ],
)
def test_broken_agent_front_matter_fails(repo: tuple[Path, str], text: str, expected: str) -> None:
    root, base = repo
    write(root, AGENT, text)
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert f"FAIL front-matter: {AGENT}" in out
    assert expected in out


def test_valid_agent_front_matter_passes(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, AGENT, AGENT_OK + "\nMore text.\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 0, out
    assert "1 file(s)" in out


def test_front_matter_is_checked_only_on_agent_files(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, "docs/planted.md", "# No front matter here\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 0, out


# ------------------------------------------------------------------ PRC-3.4 flows --decider
def test_pending_decider_cell_in_the_current_sprint_flows_file_fails(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, "docs/design/flows-sprint-05.md", flows_text("pending"))
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert "FAIL flows: docs/design/flows-sprint-05.md --review DR-05" in out
    assert "FAIL cell" in out


def test_decided_cells_pass_and_the_run_is_reported(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, "docs/design/flows-sprint-05.md", flows_text("accept (2026-11-04): ok"))
    commit(root)
    rc, out = check(root, base)
    assert rc == 0, out
    assert "flows: docs/design/flows-sprint-05.md --review DR-05 --decider product-manager: rc 0" in out


def test_flows_check_runs_even_when_the_flows_file_is_unchanged(repo: tuple[Path, str]) -> None:
    root, _ = repo
    write(root, "docs/design/flows-sprint-05.md", flows_text("pending"))
    base = commit(root, "flows")
    write(root, "docs/planted.md", "# Plain\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert "FAIL flows" in out


def test_older_sprint_flows_file_is_not_the_current_one(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, "docs/design/flows-sprint-04.md", flows_text("pending", sprint="04"))
    commit(root)
    rc, out = check(root, base)
    assert rc == 0, out
    assert "flows: docs/design/flows-sprint-05.md does not exist yet; skipped (PRC-3.4)" in out


def test_flows_file_without_a_decider_table_fails(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, "docs/design/flows-sprint-05.md", "# Flows\n\n## 14. Design review (DR-05)\n\nTBD\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert "FAIL flows: docs/design/flows-sprint-05.md" in out


# ------------------------------------------------------------------ CLI
def test_unknown_base_ref_is_a_usage_error(repo: tuple[Path, str]) -> None:
    root, _ = repo
    rc, out = check(root, "no-such-ref")
    assert rc == 2, out


def test_explicit_files_are_checked_whole(repo: tuple[Path, str]) -> None:
    root, _ = repo
    proc = run_check(root, "docs/sprints/sprint-05.md")
    assert proc.returncode == 1, proc.stdout
    assert "FAIL path: docs/sprints/sprint-05.md:3: scripts/ci/gone.py does not exist" in proc.stdout


# ------------------------------------------------------------------ ci.yml wiring
def test_ci_gate_needs_doc_check() -> None:
    assert "doc-check" in CI["jobs"]["ci-gate"]["needs"]


def test_doc_check_job_runs_check_docs_on_the_pr_diff() -> None:
    job = CI["jobs"]["doc-check"]
    runs = "\n".join(step.get("run", "") for step in job["steps"])
    assert "scripts/ci/check_docs.py" in runs
    assert "--base" in runs
    assert job["timeout-minutes"] <= 5
    checkout = next(s for s in job["steps"] if "actions/checkout" in s.get("uses", ""))
    assert checkout["with"]["fetch-depth"] == 0


def test_doc_check_is_skipped_on_drafts_and_runs_on_ready_prs_and_pushes() -> None:
    cond = CI["jobs"]["doc-check"]["if"]
    assert evaluate(cond, DRAFT_PR) is False
    assert evaluate(cond, READY_PR) is True
    assert evaluate(cond, PUSH) is True
