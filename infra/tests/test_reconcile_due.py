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
from conftest import REPO_ROOT
from reconcile_evidence import DECISIONS, LEDGER, append_ledger, init_main, merge_ticket, open_row
from reconcile_ledger import (
    PLAN_0039,
    SCRIPT,
    SPRINT_03,
    base_of_head,
    commit_base,
    git,
    ledger_section,
    live_ledger_check,
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


@pytest.mark.unit
def test_a_base_that_reads_as_a_git_option_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a git ref"):
        _module().decision_stems(tmp_path, "--output=x")


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


# PE-FIX031A-03 / SBE-FIX031A-R2-01: on a push to main the base is main itself, so a merged fix
# ticket's decisions file makes its row due until the EM writes the row. CI runs the check in
# report-only mode (due rows printed, exit 0); usage errors still fail. Negative cases first.
@pytest.mark.unit
@pytest.mark.parametrize(("due", "report_only", "rc"), [(1, False, 1), (0, False, 0), (0, True, 0)])
def test_due_rows_fail_the_check_unless_report_only(due: int, report_only: bool, rc: int) -> None:
    assert _module().exit_status(due, report_only=report_only) == rc


@pytest.mark.unit
def test_report_only_never_fails_on_due_rows() -> None:
    assert _module().exit_status(3, report_only=True) == 0


@pytest.mark.integration
def test_cli_report_only_still_refuses_a_missing_plan_file(tmp_path: Path) -> None:
    ledger = tmp_path / "rr.md"
    ledger.write_text(OPEN_05, encoding="utf-8")
    out = run_check(ledger, tmp_path / "no-such-adr.md", report_only=True)
    assert out.returncode == 2, out.stdout + out.stderr
    assert out.stderr.startswith("reconcile-due: "), out.stderr


@pytest.mark.integration
def test_main_stays_green_after_a_fix_ticket_named_after_an_open_finding_merges(
    tmp_path: Path,
) -> None:
    """PE-FIX031A-03 as reported: the real files plus a merged PE-PR24-01.md, base = HEAD.

    The real ledger closed PE-PR24-01 at the sprint close (RETRO-03), so the open row this
    case is about is appended explicitly (TCR row RETRO-03, 2026-10-15). The case relies on the
    latest ledger row naming an id winning over an earlier one: the appended Open row comes after
    the real ledger's Fixed row for PE-PR24-01, so the finding reads as open (QA-RETRO03-03)."""
    shutil.copy(SPRINT_03 / "review-rounds.md", tmp_path / "rr.md")
    with (tmp_path / "rr.md").open("a", encoding="utf-8") as ledger:
        ledger.write("\n" + OPEN_PR24)
    shutil.copy(PLAN_0039, tmp_path / "0039.md")
    shutil.copytree(SPRINT_03 / "decisions", tmp_path / "decisions")
    commit_base(tmp_path)
    (tmp_path / "decisions" / "PE-PR24-01.md").write_text("# fix ticket\n", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "merge fix ticket into main")
    main_head = git(tmp_path, "rev-parse", "HEAD").strip()
    out = live_ledger_check(
        tmp_path / "rr.md", tmp_path / "0039.md", tmp_path / "decisions", main_head
    )
    assert out.returncode == 0, out.stdout + out.stderr
    assert "PE-PR24-01 (major) named by ticket PE-PR24-01" in out.stdout


@pytest.mark.integration
def test_the_sprint_3_ledger_is_read_by_the_reconciliation_check() -> None:
    """Regression for V03R1-01 as CI runs it: the real ledger, plan and decisions parse (no
    usage error) and the due rows are printed in the job log. A due row is engineering-manager
    work (the EM status step runs the check without ``--report-only``), never a red main."""
    out = live_ledger_check(
        SPRINT_03 / "review-rounds.md", PLAN_0039, SPRINT_03 / "decisions", base_of_head()
    )
    print(out.stdout)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "reconcile-due: " in out.stdout


# C4-RECON (retro 3 B3, VM-R3-02 / verifier id V03R3-02): a merged ticket PR whose diff changes a
# file that an open row's evidence cites, with no ledger row written after that merge, is due.
# Verifier ids (``V04R1-01``) parse as finding ids. Negative cases first.
@pytest.mark.unit
@pytest.mark.parametrize(
    ("cell", "ids"),
    [
        ("V04R1-01", ["V04R1-01"]),
        ("V03R3-02", ["V03R3-02"]),
        ("VM-R3-02 (verifier id V03R3-02)", ["VM-R3-02", "V03R3-02"]),
        ("PE-R1S3-07 / QA-R3S3-04", ["PE-R1S3-07", "QA-R3S3-04"]),
        ("BLK-ASVS-6.3.3", ["BLK-ASVS-6.3.3"]),
        ("PD-RV2-DR-FE", ["PD-RV2-DR-FE"]),
        ("G03-12", ["G03-12"]),
    ],
)
def test_finding_ids_of_the_verifier_and_the_ledger_format_parse(cell: str, ids: list[str]) -> None:
    sys.path.insert(0, str(SCRIPT.parent))
    from measurelib import _FINDING_ID

    assert _FINDING_ID.findall(cell) == ids


@pytest.mark.unit
@pytest.mark.parametrize("cell", ["V04R1", "v04r1-01", "VERIFY", "R1-", "abc V04R1-x"])
def test_text_that_is_not_a_finding_id_does_not_parse(cell: str) -> None:
    sys.path.insert(0, str(SCRIPT.parent))
    from measurelib import _FINDING_ID

    assert _FINDING_ID.findall(cell) == []


@pytest.mark.unit
def test_a_ledger_row_with_only_a_verifier_id_is_counted_not_refused() -> None:
    sys.path.insert(0, str(SCRIPT.parent))
    from measurelib import open_defects

    ledger = ledger_section("VERIFY-04-r1", [("V04R1-01", "major", "**Open.** found on main")])
    assert [r["ids"] for r in open_defects(ledger)] == [["V04R1-01"]]


@pytest.mark.unit
def test_evidence_paths_are_the_file_paths_an_evidence_cell_cites() -> None:
    cell = (
        "`sed -n 35p docs/sprints/sprint-03.md` → x; `docs/decisions/0039-*.md:68` → y; "
        "`decisions/FIX-03-2b.md` row 4; `search_issues is:open label:bug` → 0"
    )
    assert _module().evidence_paths(cell) == [
        "docs/sprints/sprint-03.md",
        "docs/decisions/0039-*.md",
        "decisions/FIX-03-2b.md",
    ]


@pytest.mark.unit
def test_a_cell_without_a_file_path_cites_no_evidence() -> None:
    assert _module().evidence_paths("scorecard §12.4; rc=0, 2 open; PR #77") == []


@pytest.mark.unit
def test_a_changed_file_matches_a_cited_path_by_suffix_or_glob_only() -> None:
    m = _module()
    cited = ["decisions/FIX-03-2b.md", "docs/decisions/0039-*.md"]
    assert m.cited_changes(["docs/sprints/03/decisions/FIX-03-2b.md"], cited) == [
        "docs/sprints/03/decisions/FIX-03-2b.md"
    ]
    assert m.cited_changes(["docs/decisions/0039-ticket-map.md"], cited) == [
        "docs/decisions/0039-ticket-map.md"
    ]
    assert m.cited_changes(["docs/sprints/03/decisions/XFIX-03-2b.md", "README.md"], cited) == []


@pytest.mark.unit
def test_merges_parse_from_the_git_log_as_merged_ticket_prs() -> None:
    log = (
        "\x1eaaaaaaa1111\x1fMerge pull request #78 from o/s03/fix-03-2c-pm\x1f"
        "[FIX-03-2c] PM follow-up\n\x1d\ndocs/sprints/sprint-03.md\n"
        "\x1ebbbbbbb2222\x1fMerge branch 'main' into x\x1f\x1d\nREADME.md\n"
        "\x1eccccccc3333\x1fMerge pull request #9 from o/s04/no-title\x1f\x1d\na.md\nb.md\n"
    )
    assert _module().parse_merges(log) == [
        {
            "ticket": "FIX-03-2c",
            "pr": "#78",
            "merged_as": "aaaaaaa1111",
            "changed": ["docs/sprints/sprint-03.md"],
        },
        {
            "ticket": "s04/no-title",
            "pr": "#9",
            "merged_as": "ccccccc3333",
            "changed": ["a.md", "b.md"],
        },
    ]


@pytest.mark.integration
def test_cli_a_merge_that_changes_an_open_rows_evidence_makes_it_due(tmp_path: Path) -> None:
    init_main(tmp_path, open_row("PE-R9S9-05", "docs/design/flows.md"), ["docs/design/flows.md"])
    sha = merge_ticket(tmp_path, "FIX-09", 7, ["docs/design/flows.md"])
    out = run_check(tmp_path / LEDGER, None, tmp_path / DECISIONS, "main")
    assert out.returncode == 1, out.stdout + out.stderr
    assert (
        f"PE-R9S9-05 (major) evidence changed by ticket FIX-09 (#7) merged as {sha[:7]}"
        " (docs/design/flows.md)"
    ) in out.stdout


@pytest.mark.integration
def test_cli_a_merge_that_changes_only_the_ledger_is_not_evidence(tmp_path: Path) -> None:
    init_main(tmp_path, open_row("PE-R9S9-05", str(LEDGER)), [])
    git(tmp_path, "checkout", "-q", "-b", "s99/em")
    append_ledger(tmp_path, ledger_section("Other", [("PE-R9S9-77", "minor", "Open")]))
    git(tmp_path, "checkout", "-q", "main")
    git(tmp_path, "merge", "-q", "--no-ff", "s99/em", "-m", "Merge pull request #8 from o/s99/em")
    out = run_check(tmp_path / LEDGER, None, tmp_path / DECISIONS, "main")
    assert out.returncode == 0, out.stdout + out.stderr


@pytest.mark.integration
def test_cli_an_uncommitted_reconciliation_row_clears_the_due_row(tmp_path: Path) -> None:
    """The EM's PR writes the row: the latest row is not yet committed, so no merge is later."""
    init_main(tmp_path, open_row("PE-R9S9-05", "docs/design/flows.md"), ["docs/design/flows.md"])
    merge_ticket(tmp_path, "FIX-09", 7, ["docs/design/flows.md"])
    append_ledger(tmp_path, open_row("PE-R9S9-05", "docs/design/flows.md"), commit=False)
    out = run_check(tmp_path / LEDGER, None, tmp_path / DECISIONS, "main")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "reconcile-due: 1 open blocker/major rows, 0 due" in out.stdout


@pytest.mark.integration
def test_cli_a_merge_before_the_row_was_written_is_not_due(tmp_path: Path) -> None:
    init_main(tmp_path, "# Review rounds\n\n", ["docs/design/flows.md"])
    merge_ticket(tmp_path, "FIX-09", 7, ["docs/design/flows.md"])
    append_ledger(tmp_path, open_row("PE-R9S9-05", "docs/design/flows.md"))
    out = run_check(tmp_path / LEDGER, None, tmp_path / DECISIONS, "main")
    assert out.returncode == 0, out.stdout + out.stderr


@pytest.mark.integration
def test_cli_a_ledger_outside_a_git_repo_with_a_base_is_refused(tmp_path: Path) -> None:
    repo, outside = tmp_path / "repo", tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    init_main(repo, "# r\n", [])
    (outside / "rr.md").write_text(open_row("PE-R9S9-05", "docs/x.md"), encoding="utf-8")
    out = run_check(outside / "rr.md", None, repo / DECISIONS, "main")
    assert out.returncode == 2, out.stdout + out.stderr
    assert out.stderr.startswith("reconcile-due: "), out.stderr


@pytest.mark.unit
def test_an_evidence_cell_with_escaped_pipes_in_a_command_still_cites_its_files() -> None:
    """The FIX-03-2a row shape: ``grep '^\\| R3-9 ' f \\| grep -c x`` must not split the cell."""
    m = _module()
    ledger = (
        "| Finding | Severity | Disposition | Owner | Evidence |\n|---|---|---|---|---|\n"
        "| PD-R9S9-01 | blocker | Open | pm | `grep '^\\| R3-9 ' docs/design/flows-sprint-03.md "
        "\\| grep -c 'ba'` → 1; `sed -n 35p docs/sprints/sprint-03.md` → x |\n"
    )
    assert m.evidence_paths(m._evidence_cell(ledger.splitlines(), 3)) == [
        "docs/design/flows-sprint-03.md",
        "docs/sprints/sprint-03.md",
    ]


@pytest.mark.unit
def test_a_merge_title_names_the_finding_ids_it_carries_but_not_its_own_ticket() -> None:
    m = _module()
    assert m.title_ids("[FIX-03-2b] Meet goal metric G03-12-PE-PR24-01\n") == [
        "G03-12",
        "PE-PR24-01",
    ]
    assert m.title_ids("[PE-R9S9-05] tidy\n") == []


@pytest.mark.integration
def test_cli_a_merge_whose_title_names_an_open_finding_after_its_row_is_due(tmp_path: Path) -> None:
    init_main(tmp_path, open_row("PE-R9S9-05", "docs/design/flows.md"), ["docs/design/flows.md"])
    merge_ticket(tmp_path, "FIX-10", 8, ["docs/other.md"], title="Meet goal metric PE-R9S9-05")
    out = run_check(tmp_path / LEDGER, None, tmp_path / DECISIONS, "main")
    assert out.returncode == 1, out.stdout + out.stderr
    assert "PE-R9S9-05 (major) named by the PR title of ticket FIX-10 (#8)" in out.stdout


VM_R3_02_MAIN = "6c666b9"  # origin/main when VERIFY-03-r3 saw "0 due" (scorecard §12.4)


@pytest.mark.integration
def test_the_vm_r3_02_replay_on_the_real_history_names_both_merged_fix_tickets(
    tmp_path: Path,
) -> None:
    """VM-R3-02 as reported: at main 6c666b9 FIX-03-2b (#77) and FIX-03-2c (#78) bore on the two
    open rows and the check said "0 due". Replayed on a shared clone of the real history."""
    clone = tmp_path / "main"
    git(tmp_path, "clone", "-q", "--shared", "--no-checkout", str(REPO_ROOT), str(clone))
    git(clone, "sparse-checkout", "set", "--no-cone", "/docs/")
    git(clone, "checkout", "-q", "--detach", VM_R3_02_MAIN)
    sprint = clone / "docs" / "sprints" / "03"
    adr = next((clone / "docs" / "decisions").glob("0039-*.md"))
    out = run_check(sprint / "review-rounds.md", adr, sprint / "decisions", "HEAD")
    assert out.returncode == 1, out.stdout + out.stderr
    assert "PE-PR24-01 (major) named by the PR title of ticket FIX-03-2b (#77)" in out.stdout
    assert "evidence changed by ticket FIX-03-2c (#78)" in out.stdout
    assert "(docs/sprints/sprint-03.md)" in out.stdout
