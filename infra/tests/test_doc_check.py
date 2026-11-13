"""CI-DOC-CHECK unit tests (PRC-3.1-3.4): scripts/ci/check_docs.py run as a process, as CI runs
it, on the planted-break fixture set (doc_check_repo.py), one break per rule, negative first; and
the ci.yml wiring (a draft-skipped `doc-check` job that `ci-gate` needs)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT
from doc_check_prc11 import (
    COST_TABLE,
    SOURCES,
    SOURCES_TEXT,
    THREAT_ROW_NO_STATUS,
    THREAT_ROW_OK,
    add_threat_tool,
    reference,
    run_cost,
    threat_notes,
)
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
        (
            "Hooks run [ASB/ANT-03].",
            "FAIL citation: docs/planted.md:1: ASB/ANT-03 is Not confirmed",
        ),
        ("Flow [ASB/AGL-20], see.", "FAIL citation: docs/planted.md:1: ASB/AGL-20 is Unverified"),
        (
            "Ghost [ASB/ANT-99].",
            "FAIL citation: docs/planted.md:1: ASB/ANT-99 is not in the register",
        ),
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
        (
            AGENT_OK.replace("description: SRE / DevOps Engineer.\n", "description:\n"),
            "lacks description",
        ),
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
def test_pending_decider_cell_in_the_current_sprint_flows_file_fails(
    repo: tuple[Path, str],
) -> None:
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
    assert (
        "flows: docs/design/flows-sprint-05.md --review DR-05 --decider product-manager: rc 0"
        in out
    )


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
    write(
        root, "docs/design/flows-sprint-05.md", "# Flows\n\n## 14. Design review (DR-05)\n\nTBD\n"
    )
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
    assert (
        "FAIL path: docs/sprints/sprint-05.md:3: scripts/ci/gone.py does not exist" in proc.stdout
    )


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


# ------------------------------------------------------------------ PRC-11.1 reference citations
# CI-DOC-CHECK-06 (ADR 0056 required ticket b, extended): every content/references/** entry's
# source.citation_id is a row of docs/domain/sources.md, whether or not the change touches it.
REF = "content/references/planted/v1.json"


def test_reference_entry_citing_an_unknown_source_id_fails(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, SOURCES, SOURCES_TEXT)
    write(root, REF, reference("SRC-0001", "SRC-0999"))
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert (
        f"FAIL reference: {REF}: entries[1].source.citation_id SRC-0999 is not a row of {SOURCES}"
        in out
    )
    assert "SRC-0001" not in out


def test_reference_entries_citing_register_rows_or_footage_pass(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, SOURCES, SOURCES_TEXT)
    write(root, REF, reference("SRC-0001", "SRC-0002", None))
    commit(root)
    rc, out = check(root, base)
    assert rc == 0, out
    assert "references: 1 file(s), 2 citation(s) resolved" in out


def test_unchanged_reference_file_fails_when_its_source_row_goes(repo: tuple[Path, str]) -> None:
    root, _ = repo
    write(root, SOURCES, SOURCES_TEXT)
    write(root, REF, reference("SRC-0002"))
    base = commit(root, "reference set")
    write(root, SOURCES, SOURCES_TEXT.replace("| SRC-0002 |", "| SRC-0003 |"))
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert "entries[0].source.citation_id SRC-0002 is not a row" in out


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("{not json\n", f"FAIL reference: {REF}: does not parse as JSON"),
        (
            '{"entries": [{"source": {"citation_id": ""}}]}\n',
            "entries[0].source.citation_id '' is not a row",
        ),
        (
            '{"entries": [{"source": {"citation_id": 7}}]}\n',
            "entries[0].source.citation_id 7 is not a row",
        ),
    ],
)
def test_broken_reference_file_fails(repo: tuple[Path, str], text: str, expected: str) -> None:
    root, base = repo
    write(root, SOURCES, SOURCES_TEXT)
    write(root, REF, text)
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert expected in out


def test_reference_citation_without_a_sources_register_fails(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, REF, reference("SRC-0001"))
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert f"FAIL reference: {REF}: entries[0].source.citation_id SRC-0001: {SOURCES} not found" in out


def test_no_reference_set_yet_is_skipped_and_reported(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, "docs/planted.md", "# Plain\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 0, out
    assert "references: no content/references/**/*.json; skipped (PRC-11.1)" in out


# ------------------------------------------------------------------ PRC-11.2 threat notes
NOTES = "docs/security/threat-notes-sprint-06.md"


def test_newest_threat_notes_with_a_row_lacking_status_fails(repo: tuple[Path, str]) -> None:
    root, base = repo
    add_threat_tool(root)
    write(root, NOTES, threat_notes(THREAT_ROW_NO_STATUS))
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert f"FAIL threat-notes: {NOTES}: threat: T6-FT-1 needs 8 cells" in out


def test_threat_notes_run_even_when_the_notes_are_unchanged(repo: tuple[Path, str]) -> None:
    root, _ = repo
    add_threat_tool(root)
    write(root, NOTES, threat_notes(THREAT_ROW_NO_STATUS))
    base = commit(root, "notes")
    write(root, "docs/planted.md", "# Plain\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert "FAIL threat-notes" in out


def test_only_the_newest_threat_notes_are_checked(repo: tuple[Path, str]) -> None:
    root, base = repo
    add_threat_tool(root)
    write(root, "docs/security/threat-notes-sprint-05.md", threat_notes(THREAT_ROW_NO_STATUS, "05"))
    write(root, NOTES, threat_notes(THREAT_ROW_OK))
    commit(root)
    rc, out = check(root, base)
    assert rc == 0, out
    assert f"threat-notes: {NOTES}: rc 0" in out


def test_threat_notes_with_a_dangling_link_fail(repo: tuple[Path, str]) -> None:
    root, base = repo
    add_threat_tool(root)
    write(root, NOTES, threat_notes(THREAT_ROW_OK) + "\nSee [ADR](../decisions/9999-x.md).\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert f"FAIL threat-notes: {NOTES}: link: ../decisions/9999-x.md" in out


def test_threat_notes_without_their_checker_fail(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, NOTES, threat_notes(THREAT_ROW_OK))
    commit(root)
    rc, out = check(root, base)
    assert rc == 1, out
    assert "FAIL threat-notes: docs/security/tools/check_threat_notes.py not found" in out


def test_no_threat_notes_yet_is_skipped_and_reported(repo: tuple[Path, str]) -> None:
    root, base = repo
    write(root, "docs/planted.md", "# Plain\n")
    commit(root)
    rc, out = check(root, base)
    assert rc == 0, out
    assert "threat-notes: no docs/security/threat-notes-sprint-NN.md; skipped (PRC-11.2)" in out


# ------------------------------------------------------------------ PRC-11.3 cost per PR table
DECISIONS = "docs/sprints/06/decisions"


def cost(root: Path, title: str) -> tuple[int, str]:
    proc = run_cost(root, "--title", title)
    return proc.returncode, proc.stdout + proc.stderr


def test_ticket_pr_whose_decisions_file_has_no_cost_table_fails(repo: tuple[Path, str]) -> None:
    root, _ = repo
    write(root, f"{DECISIONS}/OPS-X.md", "# OPS-X decisions\n\n## 1. Size\n\nS.\n")
    commit(root)
    rc, out = cost(root, "[OPS-X] disk precheck")
    assert rc == 1, out
    assert f"FAIL cost-table: {DECISIONS}/OPS-X.md has no 'Cost per PR' table with a row" in out


def test_cost_table_with_a_header_but_no_row_fails(repo: tuple[Path, str]) -> None:
    root, _ = repo
    header_only = COST_TABLE.split("| implement")[0]
    write(root, f"{DECISIONS}/OPS-X.md", "# OPS-X\n\n" + header_only)
    commit(root)
    rc, out = cost(root, "[OPS-X] disk precheck")
    assert rc == 1, out
    assert "has no 'Cost per PR' table with a row" in out


def test_ticket_pr_without_a_decisions_file_fails(repo: tuple[Path, str]) -> None:
    root, _ = repo
    rc, out = cost(root, "[OPS-X] disk precheck")
    assert rc == 1, out
    assert "FAIL cost-table: no docs/sprints/<nn>/decisions/OPS-X.md" in out


def test_ticket_pr_with_a_cost_row_passes_even_if_not_measured(repo: tuple[Path, str]) -> None:
    root, _ = repo
    write(root, f"{DECISIONS}/OPS-X.md", "# OPS-X\n\n" + COST_TABLE + "\n## 2. Next\n")
    commit(root)
    rc, out = cost(root, "[OPS-X] disk precheck")
    assert rc == 0, out
    assert f"cost-table: {DECISIONS}/OPS-X.md: 1 row(s)" in out


def test_pr_title_without_a_ticket_id_is_skipped(repo: tuple[Path, str]) -> None:
    root, _ = repo
    rc, out = cost(root, "Bump actions/checkout")
    assert rc == 0, out
    assert "not a ticket PR; skipped (PRC-11.3)" in out


def test_missing_title_is_a_usage_error(repo: tuple[Path, str]) -> None:
    root, _ = repo
    proc = run_cost(root)
    assert proc.returncode == 2, proc.stdout + proc.stderr


def test_pr_policy_runs_the_cost_table_check_with_the_title_in_env() -> None:
    job = CI["jobs"]["pr-policy"]
    step = next(s for s in job["steps"] if "check_cost_table.py" in s.get("run", ""))
    assert "${{" not in step["run"], "the PR title must reach the script through env only"
    assert step["env"]["PR_TITLE"] == "${{ github.event.pull_request.title }}"
    assert evaluate(job["if"], DRAFT_PR) is False
    assert evaluate(job["if"], READY_PR) is True
