"""CI-RECON-ON-PR (PRC-4.1-4.3; retro 4 D3, E3, L13): `reconcile_due.py --pr` joins the findings
a ticket's decisions file names to the review ledger.

Unit tests drive the pure functions; integration tests run the CLI on a real git repo and on the
merged Sprint 4 decisions files, and read the `pr-policy` job of ci.yml. Negative cases first.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT
from pr_checkout import commit, git
from reconcile_on_pr import (
    DECISIONS_FILE,
    LEDGER_FILE,
    RECONCILE_STEP,
    SCRIPT,
    decisions_text,
    ledger_text,
    run_pr_check,
)


def _load():
    spec = importlib.util.spec_from_file_location("reconcile_due_pr", SCRIPT)
    assert spec is not None, f"missing {SCRIPT}"
    assert spec.loader is not None, f"missing {SCRIPT}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rd = _load()
LEDGER = ledger_text([("PE-OLD05-01 (alias QA-OLD05-02)", "major", "**Fixed**")])


# ------------------------------------------------------------------ unit: declared findings


@pytest.mark.unit
def test_an_inline_major_is_declared_with_its_severity_and_line() -> None:
    text = decisions_text("**AF-X05-01 (major):** thin library", "nothing here")
    found = rd.declared_findings(text)
    assert found == [{"id": "AF-X05-01", "severity": "major", "line": 5}]


@pytest.mark.unit
def test_an_inline_declaration_may_carry_words_after_the_severity() -> None:
    text = "new ledger finding QA-VERIFY04R4-01 (major by the RETRO-04 triage rule)\n"
    assert [f["id"] for f in rd.declared_findings(text)] == ["QA-VERIFY04R4-01"]


@pytest.mark.unit
def test_a_severity_table_row_declares_the_ids_left_of_its_severity_cell() -> None:
    text = (
        "| # | Finding | Severity | Disposition |\n|---|---|---|---|\n"
        "| 1 | PE-PLAN05-01 (alias QA-PLAN05-09) | **Major** | Fixed |\n"
        "| 2 | PLAN05-QA-01 | nit | Fixed |\n"
    )
    found = rd.declared_findings(text)
    assert [(f["id"], f["severity"], f["line"]) for f in found] == [
        ("PE-PLAN05-01", "major", 3),
        ("QA-PLAN05-09", "major", 3),
        ("PLAN05-QA-01", "nit", 4),
    ]


@pytest.mark.unit
def test_a_reference_in_a_finding_cell_is_not_declared_but_aliases_are() -> None:
    text = (
        "| # | Finding | Severity | Disposition |\n|---|---|---|---|\n"
        "| 22 | PLAN05-QA-08 (G05-06 path) | major | Fixed |\n"
        "| 23 | PE-R3-05 / QA-R3-05 (alias SQA-R3-07, see PRC-4.2) | major | Fixed |\n"
    )
    assert [f["id"] for f in rd.declared_findings(text)] == [
        "PLAN05-QA-08",
        "PE-R3-05",
        "QA-R3-05",
        "SQA-R3-07",
    ]


@pytest.mark.unit
def test_an_id_without_a_severity_is_not_a_declared_finding() -> None:
    text = decisions_text("cites AN-02 and QD-PL-03; G04-01 step 9 (judgment)")
    assert rd.declared_findings(text) == []


@pytest.mark.unit
def test_ledger_ids_are_the_first_cell_ids_of_severity_tables_aliases_included() -> None:
    assert rd.ledger_ids(LEDGER) == {"PE-OLD05-01", "QA-OLD05-02"}


@pytest.mark.unit
def test_ledger_ids_ignore_tables_without_a_severity_column() -> None:
    assert rd.ledger_ids("| Ticket | PR |\n|---|---|\n| ST-001-01 | #1 |\n") == set()


# ------------------------------------------------------------- unit: other forms (PE-CIRECON-R1-01)


@pytest.mark.unit
@pytest.mark.parametrize(
    "line",
    [
        "AF-X05-01, major: thin library",
        "(AF-X05-01, major) thin library",
        "**AF-X05-01 opened as major** (PR #27 merged with no verdict)",
        "AF-X05-01: major, thin library",
        "review finding AF-X05-01, Major: thin library",
    ],
)
def test_a_major_written_in_another_inline_form_is_declared(line: str) -> None:
    found = rd.declared_findings(decisions_text(line))
    assert [(f["id"], f["severity"]) for f in found] == [("AF-X05-01", "major")]
    assert rd.judge_decisions("d.md", decisions_text(line), None, set()) == [
        "d.md:5: AF-X05-01 (major) has no ledger row"
    ]


@pytest.mark.unit
def test_a_severity_cell_with_words_after_the_severity_is_declared() -> None:
    text = (
        "| Finding | Severity | Disposition |\n|---|---|---|\n"
        "| PE-R3S3-04 | Major (fixed in abc1234) | Fixed |\n"
        "| PE-R3S3-05 | minor, was major before triage | Fixed |\n"
    )
    found = rd.declared_findings(text)
    assert [(f["id"], f["severity"]) for f in found] == [
        ("PE-R3S3-04", "major"),
        ("PE-R3S3-05", "major"),
    ]


@pytest.mark.unit
def test_a_severity_column_left_of_the_finding_column_still_declares_the_finding() -> None:
    text = (
        "| Severity | Finding | Disposition |\n|---|---|---|\n"
        "| major | QA-ACC3-01 (alias SQA-ACC3-02) | Fixed |\n"
    )
    found = rd.declared_findings(text)
    assert [(f["id"], f["severity"]) for f in found] == [
        ("QA-ACC3-01", "major"),
        ("SQA-ACC3-02", "major"),
    ]


@pytest.mark.unit
def test_an_id_with_a_major_word_in_no_declared_form_fails_closed() -> None:
    text = decisions_text("AF-X05-07 was raised in review and triaged a blocker by the EM")
    assert rd.judge_decisions("d.md", text, None, set()) == [
        "d.md:5: AF-X05-07 sits on a line with a blocker/major word but in no declared form "
        "(PRC-4.3); write `AF-X05-07 (major)` or add its ledger row"
    ]


@pytest.mark.unit
def test_a_major_word_next_to_ledger_or_declared_ids_only_is_fine() -> None:
    text = decisions_text(
        "**AF-X05-08 (minor):** not a major issue",
        "PE-OLD05-01 was the major one and is fixed",
    )
    assert rd.judge_decisions("d.md", text, None, rd.ledger_ids(LEDGER)) == []


# ------------------------------------------------------------------ unit: judging


@pytest.mark.unit
def test_a_major_with_no_ledger_row_is_a_problem() -> None:
    text = decisions_text("**AF-X05-01 (major):** thin library")
    problems = rd.judge_decisions("d.md", text, None, rd.ledger_ids(LEDGER))
    assert problems == ["d.md:5: AF-X05-01 (major) has no ledger row"]


@pytest.mark.unit
def test_a_blocker_with_no_ledger_row_is_a_problem() -> None:
    text = decisions_text("AF-X05-04 (blocker): data loss")
    assert rd.judge_decisions("d.md", text, None, set()) == [
        "d.md:5: AF-X05-04 (blocker) has no ledger row"
    ]


@pytest.mark.unit
def test_a_major_with_a_ledger_row_under_an_alias_is_fine() -> None:
    text = decisions_text("**QA-OLD05-02 (major):** fixed here")
    assert rd.judge_decisions("d.md", text, None, rd.ledger_ids(LEDGER)) == []


@pytest.mark.unit
def test_a_minor_or_nit_needs_no_ledger_row() -> None:
    text = decisions_text("AF-X05-02 (minor): x", "AF-X05-03 (nit): y")
    assert rd.judge_decisions("d.md", text, None, set()) == []


@pytest.mark.unit
@pytest.mark.parametrize("phrase", ["known gap", "can only", "not covered", "Known Gap"])
def test_a_gap_phrase_without_a_finding_id_is_a_problem(phrase: str) -> None:
    text = decisions_text(f"the solo-wall plan ({phrase}) AN-02 QD-PL-03")
    problems = rd.judge_decisions("d.md", text, None, set())
    assert problems == [f'd.md:5: "{phrase.lower()}" line names no finding id']


@pytest.mark.unit
def test_a_gap_phrase_with_an_id_declared_in_the_same_file_is_fine() -> None:
    text = decisions_text("AF-X05-02 (minor): solo wall", "see AF-X05-02: can only say 409")
    assert rd.judge_decisions("d.md", text, None, set()) == []


@pytest.mark.unit
def test_a_gap_phrase_with_a_ledger_id_is_fine() -> None:
    text = decisions_text("PE-OLD05-01 is not covered by the stub")
    assert rd.judge_decisions("d.md", text, None, rd.ledger_ids(LEDGER)) == []


@pytest.mark.unit
def test_only_the_given_lines_are_judged() -> None:
    text = decisions_text("AF-X05-01 (major): old", "a known gap, old", "new and clean")
    assert rd.judge_decisions("d.md", text, {7}, set()) == []
    assert rd.judge_decisions("d.md", text, {5, 6}, set()) == [
        "d.md:5: AF-X05-01 (major) has no ledger row",
        'd.md:6: "known gap" line names no finding id',
    ]


@pytest.mark.unit
def test_added_lines_are_read_from_a_zero_context_diff() -> None:
    diff = (
        "diff --git a/docs/sprints/05/decisions/A.md b/docs/sprints/05/decisions/A.md\n"
        "--- a/docs/sprints/05/decisions/A.md\n+++ b/docs/sprints/05/decisions/A.md\n"
        "@@ -3,0 +4,2 @@\n+x\n+y\n@@ -9 +11 @@\n-z\n+w\n"
        "diff --git a/docs/sprints/05/decisions/B.md b/docs/sprints/05/decisions/B.md\n"
        "--- a/docs/sprints/05/decisions/B.md\n+++ b/docs/sprints/05/decisions/B.md\n"
        "@@ -1 +0,0 @@\n-gone\n"
    )
    assert rd.added_lines(diff) == {"docs/sprints/05/decisions/A.md": {4, 5, 11}}


# ------------------------------------------------------------------ integration: CLI on git


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    commit(repo, LEDGER_FILE, LEDGER)
    commit(repo, "docs/sprints/05/decisions/OLD.md", decisions_text("AF-OLD-01 (major): old"))
    git(repo, "checkout", "-q", "-b", "pr")
    return repo


@pytest.mark.integration
def test_cli_fails_on_a_planted_major_with_no_ledger_row(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    commit(repo, DECISIONS_FILE, decisions_text("**AF-PLANT05-01 (major):** thin library"))
    res = run_pr_check(repo, "--base", "main")
    assert res.returncode == 1, res.stdout + res.stderr
    assert f"{DECISIONS_FILE}:5: AF-PLANT05-01 (major) has no ledger row" in res.stdout
    assert "OLD.md" not in res.stdout  # main's own decisions lines are not the PR's


@pytest.mark.integration
def test_cli_passes_when_the_pr_writes_the_ledger_row(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    commit(repo, DECISIONS_FILE, decisions_text("**AF-PLANT05-01 (major):** thin library"))
    commit(repo, LEDGER_FILE, LEDGER + "| AF-PLANT05-01 | major | **Open.** | sre |\n")
    res = run_pr_check(repo, "--base", "main")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "0 problems" in res.stdout


@pytest.mark.integration
def test_cli_fails_on_a_gap_line_added_to_an_existing_decisions_file(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    old = "docs/sprints/05/decisions/OLD.md"
    commit(repo, old, decisions_text("AF-OLD-01 (major): old", "this is not covered yet"))
    res = run_pr_check(repo, "--base", "main")
    assert res.returncode == 1, res.stdout + res.stderr
    assert f'{old}:6: "not covered" line names no finding id' in res.stdout.splitlines()


@pytest.mark.integration
def test_cli_passes_when_no_decisions_file_changed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    commit(repo, "docs/notes.md", "a known gap outside decisions files\n")
    res = run_pr_check(repo, "--base", "main")
    assert res.returncode == 0, res.stdout + res.stderr


@pytest.mark.integration
def test_cli_refuses_an_unreadable_base(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    res = run_pr_check(repo, "--base", "no-such-ref")
    assert res.returncode == 2, res.stdout + res.stderr
    assert "reconcile-due" in res.stderr


@pytest.mark.integration
def test_cli_refuses_a_base_that_looks_like_an_option(tmp_path: Path) -> None:
    res = run_pr_check(_repo(tmp_path), "--base=--output=x")
    assert res.returncode == 2


@pytest.mark.integration
def test_cli_on_an_empty_range_passes() -> None:
    res = run_pr_check(REPO_ROOT, "--base", "HEAD")
    assert res.returncode == 0, res.stdout + res.stderr


@pytest.mark.integration
def test_cli_without_pr_still_needs_a_ledger() -> None:
    res = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, timeout=60)
    assert res.returncode == 2
    assert "ledger" in res.stderr


@pytest.mark.integration
def test_cli_on_the_merged_sprint_4_decisions_flags_st_062_part2() -> None:
    files = sorted(str(p) for p in (REPO_ROOT / "docs/sprints/04/decisions").glob("*.md"))
    res = run_pr_check(REPO_ROOT, "--files", *files)
    assert res.returncode == 1, res.stdout + res.stderr
    flagged = [line for line in res.stdout.splitlines() if "ST-062-part2.md:12:" in line]
    assert flagged == [
        'docs/sprints/04/decisions/ST-062-part2.md:12: "can only" line names no finding id'
    ]


@pytest.mark.integration
def test_cli_reads_the_other_major_forms_in_the_merged_sprint_3_decisions(tmp_path: Path) -> None:
    """PE-CIRECON-R1-01: the four lines the review named, judged without their ledger rows."""
    lines = {"C3-03.md": 3, "PE-R3S3-04.md": 3, "QA-ACC-3.md": 16, "RETRO-03.md": 10}
    out_dir = tmp_path / "docs/sprints/03/decisions"
    out_dir.mkdir(parents=True)
    for name in lines:
        src = REPO_ROOT / "docs/sprints/03/decisions" / name
        (out_dir / name).write_text(src.read_text("utf-8"), "utf-8")
    res = run_pr_check(tmp_path, "--files", *sorted(str(out_dir / n) for n in lines))
    assert res.returncode == 1, res.stdout + res.stderr
    for name, number in lines.items():
        where = f"docs/sprints/03/decisions/{name}:{number}: "
        assert any(where in line for line in res.stdout.splitlines()), where


# ------------------------------------------------------------------ the pr-policy job


@pytest.mark.unit
def test_pr_policy_runs_the_reconcile_step_against_the_base_branch() -> None:
    jobs = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text())["jobs"]
    steps = {s.get("name"): s for s in jobs["pr-policy"]["steps"]}
    step = steps[RECONCILE_STEP]
    assert step["run"].startswith("python3 scripts/measure/reconcile_due.py --pr ")
    assert '--base "origin/$BASE_REF"' in step["run"]
    assert "--report-only" not in step["run"]
    assert step["env"]["BASE_REF"] == "${{ github.base_ref }}"
    assert "pr-policy" in jobs["ci-gate"]["needs"]


# ------------------------------------------------------------------ PRC-4.3: the id format


@pytest.mark.unit
def test_the_finding_id_format_is_written_next_to_the_pattern_and_in_the_runbook() -> None:
    lib = (REPO_ROOT / "scripts/measure/measurelib.py").read_text()
    before = lib[: lib.index("_FINDING_ID = re.compile(")]
    assert "Finding-id format (PRC-4.3)" in before
    runbook = (REPO_ROOT / "docs/ops/evidence-runs.md").read_text()
    assert "## Finding-id format (PRC-4.3)" in runbook
    assert "reconcile_due.py --pr" in runbook
