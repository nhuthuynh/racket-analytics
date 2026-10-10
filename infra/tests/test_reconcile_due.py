"""FIX-03-1a (G03-12, V03R1-01): open review-rounds rows that a merged ticket names are due.

Unit tests drive the pure functions; integration tests run the CLI on files, including the real
Sprint 3 ledger, ADR 0039 plan and ticket decision files. Negative cases first.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from reconcile_ledger import (
    PLAN_0039,
    SCRIPT,
    SPRINT_03,
    base_of_head,
    commit_base,
    git,
    ledger_section,
    plan,
    run_check,
)


def _module():  # loaded from scripts/measure, not a package
    spec = importlib.util.spec_from_file_location("reconcile_due", SCRIPT)
    assert spec is not None, f"missing {SCRIPT}"
    assert spec.loader is not None, f"missing {SCRIPT}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


OPEN_05 = ledger_section("Sprint close", [("PE-R9S9-05 / QA-R9S9-03", "major", "**Open.** x")])
PLAN_12 = plan(
    [("PE-R9S9-07", "#12", "4f5b8f1")], [("8be152d", "ci(PE-R9S9-05)", "PE-R9S9-07 (#12)")]
)


# ---------------------------------------------------------------- unit: negative cases first
@pytest.mark.unit
def test_a_ledger_without_a_review_table_is_refused() -> None:
    with pytest.raises(ValueError, match="no review table"):
        _module().due_rows("# nothing\n", [])


@pytest.mark.unit
def test_an_open_row_named_by_a_merged_commit_scope_is_due() -> None:
    m = _module()
    due = m.due_rows(OPEN_05, m.ticket_index(PLAN_12, []))
    assert [(d["ids"], [t["ticket"] for t in d["tickets"]]) for d in due] == [
        (["PE-R9S9-05", "QA-R9S9-03"], ["PE-R9S9-07"])
    ]
    assert due[0]["tickets"][0]["pr"] == "#12"
    assert due[0]["tickets"][0]["merged_as"] == "4f5b8f1"


@pytest.mark.unit
def test_an_alias_id_in_a_commit_scope_also_makes_the_row_due() -> None:
    m = _module()
    plan_alias = plan([("T-1", "#3", "aaaaaaa")], [("1111111", "docs(X-1,QA-R9S9-03)", "T-1 (#3)")])
    assert len(m.due_rows(OPEN_05, m.ticket_index(plan_alias, []))) == 1


@pytest.mark.unit
def test_a_decision_file_named_after_the_finding_makes_the_row_due() -> None:
    m = _module()
    ledger = ledger_section("S", [("PE-R9S9-03", "major", "Open, partly fixed")])
    due = m.due_rows(ledger, m.ticket_index("", ["PE-R9S9-03-ITS"]))
    assert [t["ticket"] for t in due[0]["tickets"]] == ["PE-R9S9-03-ITS"]


@pytest.mark.unit
def test_a_decision_file_of_a_longer_id_does_not_name_the_finding() -> None:
    m = _module()
    ledger = ledger_section("S", [("PE-R9S9-0", "major", "Open")])
    assert m.due_rows(ledger, m.ticket_index("", ["PE-R9S9-03"])) == []


@pytest.mark.unit
def test_the_finding_id_cell_alone_never_reconciles_its_own_ticket() -> None:
    m = _module()
    ledger = ledger_section("S", [("PE-R9S9-04", "major", "Open. Ticket map rows missing")])
    assert len(m.due_rows(ledger, m.ticket_index("", ["PE-R9S9-04"]))) == 1


@pytest.mark.unit
@pytest.mark.parametrize("mention", ["ticket PE-R9S9-07", "PR #12", "merged as `4f5b8f1`"])
def test_a_row_that_names_the_ticket_pr_or_merge_commit_is_reconciled(mention: str) -> None:
    m = _module()
    ledger = ledger_section("S", [("PE-R9S9-05", "major", f"Open: still red after {mention}")])
    assert m.due_rows(ledger, m.ticket_index(PLAN_12, [])) == []


@pytest.mark.unit
def test_a_section_heading_that_names_the_merge_commit_reconciles_its_rows() -> None:
    m = _module()
    ledger = ledger_section(
        "Ticket X at `origin/main` `4f5b8f1`", [("PE-R9S9-05", "major", "Open")]
    )
    assert m.due_rows(ledger, m.ticket_index(PLAN_12, [])) == []


@pytest.mark.unit
def test_a_pr_number_is_matched_whole_not_as_a_prefix() -> None:
    m = _module()
    ledger = ledger_section("S", [("PE-R9S9-05", "major", "Open: see PR #123")])
    assert len(m.due_rows(ledger, m.ticket_index(PLAN_12, []))) == 1


@pytest.mark.unit
def test_a_fixed_row_is_never_due() -> None:
    m = _module()
    ledger = ledger_section("S", [("PE-R9S9-05", "major", "**Fixed** by the owner")])
    assert m.due_rows(ledger, m.ticket_index(PLAN_12, [])) == []


@pytest.mark.unit
def test_a_commit_row_without_a_pr_is_not_a_merged_ticket() -> None:
    m = _module()
    plan_none = plan([], [("2222222", "docs(PE-R9S9-05)", "— (merge, no PR)")])
    assert m.ticket_index(plan_none, []) == []


# ---------------------------------------------------------------- integration: the CLI
@pytest.mark.integration
def test_cli_refuses_a_missing_plan_file(tmp_path: Path) -> None:
    ledger = tmp_path / "rr.md"
    ledger.write_text(OPEN_05, encoding="utf-8")
    out = run_check(ledger, tmp_path / "no-such-adr.md")
    assert out.returncode == 2, out.stdout + out.stderr
    assert out.stderr.startswith("reconcile-due: "), out.stderr


@pytest.mark.integration
def test_cli_refuses_a_missing_decisions_dir(tmp_path: Path) -> None:
    ledger = tmp_path / "rr.md"
    ledger.write_text(OPEN_05, encoding="utf-8")
    out = run_check(ledger, None, tmp_path / "no-such-dir")
    assert out.returncode == 2, out.stdout + out.stderr


@pytest.mark.integration
def test_cli_names_the_due_row_with_its_line_and_writes_json(tmp_path: Path) -> None:
    ledger = tmp_path / "rr.md"
    ledger.write_text(OPEN_05, encoding="utf-8")
    adr = tmp_path / "0039.md"
    adr.write_text(PLAN_12, encoding="utf-8")
    report = tmp_path / "out" / "due.json"
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(ledger), "--plan", str(adr), "--json", str(report)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert out.returncode == 1, out.stdout + out.stderr
    assert "due: line 5: PE-R9S9-05 / QA-R9S9-03 (major)" in out.stdout
    assert "ticket PE-R9S9-07 (#12) merged as 4f5b8f1" in out.stdout
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["open"] == 1
    assert data["due"] == 1


# PE-FIX031A-01: a ticket PR adds its decisions file before it merges, so only the decisions
# files on the base branch name merged tickets. Negative case first.
OPEN_PR24 = ledger_section("S", [("PE-PR24-01", "major", "**Open.** F1")])


def _repo_with_open_row(tmp_path: Path) -> tuple[Path, Path, str]:
    (tmp_path / "decisions").mkdir()
    (tmp_path / "decisions" / "OTHER-1.md").write_text("# d\n", encoding="utf-8")
    ledger = tmp_path / "rr.md"
    ledger.write_text(OPEN_PR24, encoding="utf-8")
    return ledger, tmp_path / "decisions", commit_base(tmp_path)


@pytest.mark.integration
def test_cli_a_decision_file_not_yet_on_the_base_names_no_merged_ticket(tmp_path: Path) -> None:
    ledger, decisions, base = _repo_with_open_row(tmp_path)
    (decisions / "PE-PR24-01.md").write_text("# the fix ticket's own PR\n", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "ticket PR")
    out = run_check(ledger, None, decisions, base)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "reconcile-due: 1 open blocker/major rows, 0 due" in out.stdout


@pytest.mark.integration
def test_cli_an_untracked_decision_file_names_no_merged_ticket(tmp_path: Path) -> None:
    ledger, decisions, base = _repo_with_open_row(tmp_path)
    (decisions / "PE-PR24-01.md").write_text("# not committed\n", encoding="utf-8")
    assert run_check(ledger, None, decisions, base).returncode == 0


@pytest.mark.integration
def test_cli_refuses_a_base_ref_git_cannot_resolve(tmp_path: Path) -> None:
    ledger, decisions, _ = _repo_with_open_row(tmp_path)
    out = run_check(ledger, None, decisions, "no-such-ref")
    assert out.returncode == 2, out.stdout + out.stderr
    assert out.stderr.startswith("reconcile-due: "), out.stderr


@pytest.mark.integration
def test_cli_a_decision_file_on_the_base_names_its_merged_ticket(tmp_path: Path) -> None:
    (tmp_path / "decisions").mkdir()
    (tmp_path / "decisions" / "PE-PR24-01.md").write_text("# merged\n", encoding="utf-8")
    ledger = tmp_path / "rr.md"
    ledger.write_text(OPEN_PR24, encoding="utf-8")
    base = commit_base(tmp_path)
    out = run_check(ledger, None, tmp_path / "decisions", base)
    assert out.returncode == 1, out.stdout + out.stderr
    assert "PE-PR24-01 (major) named by ticket PE-PR24-01" in out.stdout


@pytest.mark.integration
def test_a_fix_ticket_named_after_an_open_sprint_3_finding_passes_on_its_own_pr(
    tmp_path: Path,
) -> None:
    """PE-FIX031A-01 as reported: the real ledger, plan and decisions, plus PE-PR24-01.md."""
    shutil.copy(SPRINT_03 / "review-rounds.md", tmp_path / "rr.md")
    shutil.copy(PLAN_0039, tmp_path / "0039.md")
    shutil.copytree(SPRINT_03 / "decisions", tmp_path / "decisions")
    base = commit_base(tmp_path)
    (tmp_path / "decisions" / "PE-PR24-01.md").write_text("# fix ticket\n", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "fix ticket PR")
    out = run_check(tmp_path / "rr.md", tmp_path / "0039.md", tmp_path / "decisions", base)
    assert out.returncode == 0, out.stdout + out.stderr


@pytest.mark.integration
def test_the_sprint_3_ledger_has_no_open_row_a_merged_ticket_names_unreconciled() -> None:
    """Regression for V03R1-01: six rows read open on main after their tickets merged.

    Only decisions files on the base (merge base with ``origin/main``) name merged tickets.
    """
    out = run_check(
        SPRINT_03 / "review-rounds.md", PLAN_0039, SPRINT_03 / "decisions", base_of_head()
    )
    assert out.returncode == 0, out.stdout + out.stderr
