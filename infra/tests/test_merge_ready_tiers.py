"""CI-TIERS-b (PRC-2.4-2.7; ADR 0056 decision 2): `scripts/ci/merge_ready.py` requires the
verdict set of the PR's computed review tier, and ignores an APPROVE from the PR's author role.

  T0: one APPROVE on the head from any role but the author's, plus `doc-check` success.
  T1: principal-engineer + senior-qa-engineer APPROVE on the head, plus `ci-gate` success.
  T2: T1 + security-privacy-engineer on every tier 2 PR + each flagged specialist.

The author role is computed from the head branch `s<nn>/<id>` and the row of
`docs/sprints/<nn>/ticket-owners.json` on main (or the fixed `BOOTSTRAP_OWNERS` table in
`review_tiers.py`), never from the PR body, labels or comments. Unit tests drive the pure
rules; integration tests run the script over HTTP against `github_stub.py`. Negative cases first.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR
from github_stub import (
    HEAD_SHA,
    OWNERS_05,
    GitHubStub,
    changed,
    check_run,
    green_runs,
    owners_json,
    review,
    serve,
)
from test_merge_ready import run_script

DOC_CHECK = "Doc checks (paths, citations, agent front matter, decider cells)"
PE, QA, SEC = "principal-engineer", "senior-qa-engineer", "security-privacy-engineer"
SRE, EM, BE = "sre-devops-engineer", "engineering-manager", "senior-backend-engineer"
# The §15 "Owner" column abbreviations (docs/sprints/sprint-05.md §15).
ABBREV = {
    "sre": SRE,
    "qa": QA,
    "pm": "product-manager",
    "ba": "business-analyst",
    "pe": PE,
    "sec": SEC,
    "pd": "principal-designer",
    "coach": "pickleball-domain-coach",
    "em": EM,
    "be": BE,
    "fe": "senior-frontend-engineer",
    "ml": "senior-ml-cv-engineer",
}


def _load(name: str) -> ModuleType:
    path = SCRIPTS_DIR / "ci" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses resolve their module by name
    spec.loader.exec_module(mod)
    return mod


def mr() -> ModuleType:
    return _load("merge_ready")


def t0_runs() -> list[dict[str, Any]]:
    return [*green_runs(), check_run(DOC_CHECK, run_id=30)]


def approve(*roles: str, sha: str = HEAD_SHA) -> list[dict[str, Any]]:
    return [review(role, "APPROVE", sha, 10 + i) for i, role in enumerate(roles)]


def run(stub: GitHubStub) -> subprocess.CompletedProcess[str]:
    with serve(stub):
        return run_script(stub)


def refused(res: subprocess.CompletedProcess[str], *words: str) -> None:
    assert res.returncode == 1, res.stdout + res.stderr
    assert "merge-ready: no" in res.stdout
    for word in words:
        assert word in res.stdout, res.stdout


def allowed(res: subprocess.CompletedProcess[str]) -> None:
    assert res.returncode == 0, res.stdout + res.stderr
    assert "merge-ready: yes" in res.stdout


def loader(files: dict[str, bytes]) -> Callable[[str], bytes | None]:
    """The owner-file reader `resolve_author` takes: sprint "05" -> the file on main, or None."""
    return files.get


S05 = {"05": owners_json([("s05/ci-tiers-b", SRE), ("s05/st-075a", BE)])}


# ================================================== unit: author role (PRC-2.7), negatives first
@pytest.mark.unit
@pytest.mark.parametrize("branch", ["feature/x", "s5/x", "s05", "S05/X", "s05/", "main"])
def test_a_branch_of_another_shape_fails_closed(branch: str) -> None:
    role, problems = mr().resolve_author(branch, 1, loader(S05))
    assert role is None
    assert any(branch in p and "s<nn>/<id>" in p for p in problems), problems


@pytest.mark.unit
def test_a_branch_with_no_row_fails_closed_naming_the_owners_step() -> None:
    role, problems = mr().resolve_author("s05/new-ticket", 1, loader(S05))
    assert role is None
    assert any("s05/new-ticket" in p and "s05/owners-<slug>" in p for p in problems), problems


@pytest.mark.unit
def test_two_rows_for_one_branch_fail_closed_naming_them() -> None:
    dup = {"05": owners_json([("s05/ci-tiers-b", SRE), ("s05/ci-tiers-b", BE)])}
    role, problems = mr().resolve_author("s05/ci-tiers-b", 1, loader(dup))
    assert role is None
    assert any("s05/ci-tiers-b" in p and "rows" in p for p in problems), problems


@pytest.mark.unit
@pytest.mark.parametrize("owner", ["sre", "orchestrator", "", "Principal-Engineer"])
def test_an_owner_that_is_not_a_role_file_fails_closed(owner: str) -> None:
    bad = {"05": owners_json([("s05/ci-tiers-b", owner)])}
    role, problems = mr().resolve_author("s05/ci-tiers-b", 1, loader(bad))
    assert role is None
    assert any("s05/ci-tiers-b" in p and "not a role file" in p for p in problems), problems


@pytest.mark.unit
@pytest.mark.parametrize("data", [b"not json", b"[]", b'{"tickets": {}}', b'{"tickets": [1]}'])
def test_a_malformed_owner_file_fails_closed(data: bytes) -> None:
    role, problems = mr().resolve_author("s05/ci-tiers-b", 1, loader({"05": data}))
    assert role is None
    assert any("docs/sprints/05/ticket-owners.json" in p for p in problems), problems


@pytest.mark.unit
def test_a_sprint_without_an_owner_file_fails_closed_naming_the_bootstrap_step() -> None:
    role, problems = mr().resolve_author("s06/st-090", 1, loader(S05))
    assert role is None
    assert (
        "no docs/sprints/06/ticket-owners.json on main: merge s06/plan first (bootstrap step)"
        in problems
    )


@pytest.mark.unit
def test_a_bootstrap_branch_with_a_conflicting_row_fails_closed() -> None:
    conflict = {"05": owners_json([("s05/plan", SRE)])}
    role, problems = mr().resolve_author("s05/plan", 2, loader(conflict))
    assert role is None
    assert any("s05/plan" in p and "conflict" in p for p in problems), problems


@pytest.mark.unit
@pytest.mark.parametrize("tier", [1, 2])
def test_a_docs_branch_with_a_code_file_fails_closed(tier: int) -> None:
    role, problems = mr().resolve_author("docs/audit-x", tier, loader({}))
    assert role is None
    assert any("open an s<nn>/<id> ticket" in p for p in problems), problems


@pytest.mark.unit
def test_an_ambiguous_branch_prefix_fails_closed() -> None:
    both = {"05": owners_json([("s05/ci-tiers", SRE), ("s05/ci-tiers-b", BE)])}
    role, problems = mr().resolve_author("s05/ci-tiers-b-slug", 1, loader(both))
    assert role is None
    assert any("s05/ci-tiers" in p and "s05/ci-tiers-b" in p for p in problems), problems


@pytest.mark.unit
@pytest.mark.parametrize(
    ("branch", "tier", "files", "owner"),
    [
        ("s05/ci-tiers-b", 2, S05, SRE),
        ("s05/ci-tiers-b-merge-ready-py-verdict-sets", 2, S05, SRE),  # the lane's slug suffix
        ("s05/st-075a", 2, S05, BE),
        ("s06/plan", 2, {}, EM),  # (a) bootstrap, no Sprint 6 file
        ("s05/plan", 2, S05, EM),
        ("s05/ci-fix-red-main", 1, S05, SRE),  # (b)
        ("s05/owners-st-099", 2, S05, EM),
        ("docs/audit-x", 0, {}, EM),  # (c) only at tier 0
        ("s05/plan", 2, {"05": owners_json([("s05/plan", EM)])}, EM),  # agreeing row
    ],
)
def test_the_author_role_is_the_owner_row_or_the_bootstrap_entry(
    branch: str, tier: int, files: dict[str, bytes], owner: str
) -> None:
    assert mr().resolve_author(branch, tier, loader(files)) == (owner, [])


@pytest.mark.unit
def test_a_close_pr_resolves_from_its_own_sprint_after_the_next_sprint_file_exists() -> None:
    files = {
        "05": owners_json([("s05/retro-05", EM)]),
        "06": owners_json([("s06/plan", EM), ("s06/st-090", SRE)], sprint=6),
    }
    assert mr().resolve_author("s05/retro-05", 0, loader(files)) == (EM, [])


@pytest.mark.unit
def test_the_bootstrap_table_lives_in_review_tiers() -> None:
    owners = {owner for _, owner, _ in _load("review_tiers").BOOTSTRAP_OWNERS}
    assert owners == {EM, SRE}


@pytest.mark.unit
def test_the_twelve_roles_are_the_role_files() -> None:
    files = {p.stem for p in (REPO_ROOT / ".claude" / "agents").glob("*.md")}
    assert set(mr().ROLES) == files
    assert len(files) == 12


@pytest.mark.unit
def test_the_doc_check_name_is_the_ci_job_name() -> None:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert f"    name: {mr().DOC_CHECK}\n" in ci


# ================================================== unit: verdict sets per tier (PRC-2.4-2.6)
def evaluate(
    tier: int,
    reviews: list[dict[str, Any]],
    author: str | None = SRE,
    specialists: frozenset[str] = frozenset(),
    runs: list[dict[str, Any]] | None = None,
) -> list[str]:
    mod = mr()
    gate = mod.Gate(tier, author, specialists)
    pr = {"state": "open", "head": {"sha": HEAD_SHA}, "base": {"ref": "main"}}
    return list(mod.evaluate(pr, HEAD_SHA, t0_runs() if runs is None else runs, reviews, (), gate))


@pytest.mark.unit
def test_tier_0_without_the_doc_check_fails() -> None:
    reasons = evaluate(0, approve(PE), runs=green_runs())
    assert any(DOC_CHECK in r for r in reasons), reasons


@pytest.mark.unit
def test_tier_0_with_only_the_author_roles_approve_fails_naming_it() -> None:
    reasons = evaluate(0, approve(SRE))
    assert any(SRE in r and "author" in r for r in reasons), reasons


@pytest.mark.unit
def test_tier_0_passes_with_one_other_role_and_the_doc_check_without_ci_gate() -> None:
    runs = [r for r in t0_runs() if r["name"] != "ci-gate"]
    assert evaluate(0, approve("principal-designer"), runs=runs) == []


@pytest.mark.unit
@pytest.mark.parametrize("name", ["engineering-managers", "doc-reviewer", "principal-engineers"])
def test_tier_0_ignores_an_approve_from_a_name_that_is_not_a_role(name: str) -> None:
    """PE-193-01: only the 12 role files count, so a one-character variant of the author's
    role (or any made-up name) never satisfies tier 0."""
    reasons = evaluate(0, approve(name), author=EM)
    assert any("tier 0" in r for r in reasons), reasons


@pytest.mark.unit
def test_verdicts_keeps_only_role_file_approvals_but_any_changes_requested_blocks() -> None:
    """PE-193-01: an unknown name never approves; its CHANGES REQUESTED still blocks (fail
    closed, a typo in a blocking review must not unblock the PR)."""
    mod = mr()
    found = mod.verdicts([*approve("doc-reviewer", PE)])
    assert set(found) == {PE}, found
    blocked = [review("doc-reviewer", "CHANGES REQUESTED", review_id=40), *approve(PE)]
    reasons = evaluate(0, blocked, author=EM)
    assert any("doc-reviewer" in r and "CHANGES REQUESTED" in r for r in reasons), reasons


@pytest.mark.unit
def test_tier_1_with_principal_and_senior_backend_fails_naming_qa() -> None:
    reasons = evaluate(1, approve(PE, BE))
    assert any(QA in r for r in reasons), reasons


@pytest.mark.unit
def test_tier_1_without_ci_gate_fails() -> None:
    runs = [r for r in t0_runs() if r["name"] != "ci-gate"]
    assert any("ci-gate" in r for r in evaluate(1, approve(PE, QA), runs=runs))


@pytest.mark.unit
def test_tier_1_with_the_qa_author_ignores_qas_own_approve() -> None:
    reasons = evaluate(1, approve(PE, QA), author=QA)
    assert any(QA in r and "author" in r for r in reasons), reasons


@pytest.mark.unit
def test_tier_1_passes_with_principal_and_qa() -> None:
    assert evaluate(1, approve(PE, QA)) == []


@pytest.mark.unit
def test_tier_2_without_security_fails_naming_it() -> None:
    reasons = evaluate(2, approve(PE, QA))
    assert any(SEC in r for r in reasons), reasons


@pytest.mark.unit
def test_tier_2_needs_each_flagged_specialist() -> None:
    reasons = evaluate(2, approve(PE, QA, SEC), specialists=frozenset({"principal-designer"}))
    assert any("principal-designer" in r for r in reasons), reasons


@pytest.mark.unit
def test_tier_2_passes_with_the_full_set() -> None:
    reviews = approve(PE, QA, SEC, "principal-designer")
    assert evaluate(2, reviews, specialists=frozenset({"principal-designer"})) == []


@pytest.mark.unit
def test_an_author_resolution_problem_blocks_even_with_every_verdict() -> None:
    mod = mr()
    gate = mod.Gate(1, None, frozenset(), ("no row for s05/x",))
    pr = {"state": "open", "head": {"sha": HEAD_SHA}, "base": {"ref": "main"}}
    reasons = mod.evaluate(pr, HEAD_SHA, t0_runs(), approve(PE, QA, SEC), (), gate)
    assert "no row for s05/x" in reasons


# ====================================== §15 drift test (PRC-2.7: the Markdown is the human view)
def section_15(md: str) -> dict[str, str]:
    """Branch -> owner role from the §15 ticket map ("| Ticket | Branch | Owner | ...")."""
    part = md.split("\n## 15.", 1)[1].split("\n## ", 1)[0]
    rows = {}
    for line in part.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) > 3 and cells[1].startswith("`s"):
            rows[cells[1].strip("`")] = ABBREV.get(cells[2], f"<unknown {cells[2]!r}>")
    return rows


def owner_rows(data: bytes | str) -> dict[str, str]:
    return {t["branch"]: t["owner"] for t in json.loads(data)["tickets"]}


def drift(md: str, owners: bytes | str) -> list[str]:
    plan, rows = section_15(md), owner_rows(owners)
    return [
        f"{b}: §15 says {plan.get(b)}, ticket-owners.json says {rows.get(b)}"
        for b in sorted(set(plan) | set(rows))
        if plan.get(b) != rows.get(b)
    ]


def sprints_with_owner_files() -> list[Path]:
    return sorted((REPO_ROOT / "docs" / "sprints").glob("*/ticket-owners.json"))


@pytest.mark.unit
def test_ticket_owner_map_matches_plan_section_15() -> None:
    files = sprints_with_owner_files()
    assert files, "no docs/sprints/*/ticket-owners.json"
    for owners in files:
        plan = REPO_ROOT / "docs" / "sprints" / f"sprint-{owners.parent.name}.md"
        assert drift(plan.read_text(), owners.read_bytes()) == [], owners


@pytest.mark.unit
def test_a_section_15_owner_only_edit_fails_drift_and_leaves_the_author_unchanged() -> None:
    md = (REPO_ROOT / "docs" / "sprints" / "sprint-05.md").read_text()
    owners = (REPO_ROOT / OWNERS_05).read_bytes()
    edited = md.replace("| `s05/ci-tiers-b` | sre |", "| `s05/ci-tiers-b` | pe |", 1)
    assert edited != md
    assert drift(edited, owners) == [
        "s05/ci-tiers-b: §15 says principal-engineer, ticket-owners.json says sre-devops-engineer"
    ]
    load = loader({"05": owners})
    assert mr().resolve_author("s05/ci-tiers-b", 2, load) == (SRE, [])


# ============================================ integration: over HTTP against the GitHub stub
@pytest.mark.integration
def test_script_t0_docs_pr_passes() -> None:
    stub = GitHubStub(files=changed("docs/process/x.md"), check_runs=t0_runs())
    stub.reviews = approve("principal-designer")
    res = run(stub)
    allowed(res)
    assert "review-tier: 0" in res.stdout


@pytest.mark.integration
def test_script_t0_with_a_hidden_executable_file_is_tier_1() -> None:
    stub = GitHubStub(files=changed("docs/process/x.md", "docs/process/run"), check_runs=t0_runs())
    stub.modes["docs/process/run"] = "100755"
    stub.reviews = approve("principal-designer")
    refused(run(stub), PE, QA, "review-tier: 1")


@pytest.mark.integration
def test_script_t1_principal_and_senior_backend_fails() -> None:
    stub = GitHubStub()
    stub.reviews = approve(PE, BE)
    refused(run(stub), QA)


@pytest.mark.integration
@pytest.mark.parametrize(
    "path",
    [
        "backend/src/racket/video_ingest/upload.py",  # security path
        "backend/src/racket/migrations/versions/0009_x.py",  # schema
        "docs/architecture/api-matches.md",  # API contract
        "newdir/thing.bin",  # unmatched, fail closed
    ],
    ids=["security", "migration", "api-contract", "unmatched"],
)
def test_script_t2_principal_and_qa_without_security_fails(path: str) -> None:
    stub = GitHubStub(files=changed(path))
    stub.reviews = approve(PE, QA)
    refused(run(stub), SEC, "review-tier: 2")


@pytest.mark.integration
def test_script_t2_with_security_passes() -> None:
    stub = GitHubStub(files=changed("backend/src/racket/migrations/versions/0009_x.py"))
    stub.reviews = approve(PE, QA, SEC)
    allowed(run(stub))


@pytest.mark.integration
def test_script_ignores_a_planted_wrong_role_approve() -> None:
    stub = GitHubStub(files=changed("docs/process/x.md"), check_runs=t0_runs())
    stub.reviews = approve(SRE)  # the head branch s05/ci-tiers-b is owned by sre
    refused(run(stub), SRE, "author")


@pytest.mark.integration
def test_script_takes_the_author_from_the_owner_file_not_the_pr_body() -> None:
    stub = GitHubStub(files=changed("docs/process/x.md"), check_runs=t0_runs())
    stub.pr["body"] = "Author role: principal-engineer\nReviewer: principal-engineer"
    stub.reviews = approve(SRE)
    res = run(stub)
    refused(res, SRE)
    assert f"author-role: {SRE}" in res.stdout


@pytest.mark.integration
def test_script_a_branch_with_no_row_fails_closed() -> None:
    stub = GitHubStub()
    stub.pr["head"]["ref"] = "s05/new-ticket"
    stub.reviews = approve(PE, QA)
    refused(run(stub), "s05/new-ticket", "s05/owners-<slug>")


@pytest.mark.integration
def test_script_a_branch_adding_its_own_row_is_still_checked_against_main() -> None:
    stub = GitHubStub(files=changed(TIER1 := "backend/src/racket/analytics/x.py", OWNERS_05))
    stub.pr["head"]["ref"] = "s05/new-ticket"
    head_rows = owners_json([("s05/ci-tiers-b", SRE), ("s05/new-ticket", BE)])
    stub.contents[(OWNERS_05, HEAD_SHA)] = head_rows
    stub.reviews = approve(PE, QA, SEC)
    refused(run(stub), "s05/new-ticket", "s05/owners-<slug>")
    assert TIER1


@pytest.mark.integration
def test_script_an_owner_that_is_not_a_role_file_fails_closed() -> None:
    stub = GitHubStub()
    stub.contents[(OWNERS_05, "main")] = owners_json([("s05/ci-tiers-b", "orchestrator")])
    stub.reviews = approve(PE, QA)
    refused(run(stub), "s05/ci-tiers-b", "orchestrator")


@pytest.mark.integration
def test_script_an_owner_file_only_change_is_tier_2() -> None:
    stub = GitHubStub(files=changed(OWNERS_05))
    stub.reviews = approve(PE, QA)
    refused(run(stub), SEC, "review-tier: 2")


@pytest.mark.integration
def test_script_bootstrap_plan_of_a_new_sprint_passes_and_a_ticket_of_it_fails() -> None:
    plan = GitHubStub(files=changed("docs/sprints/06/ticket-owners.json"))
    plan.pr["head"]["ref"] = "s06/plan"
    plan.reviews = approve(PE, QA, SEC)
    res = run(plan)
    allowed(res)
    assert f"author-role: {EM}" in res.stdout
    ticket = GitHubStub()
    ticket.pr["head"]["ref"] = "s06/st-090"
    ticket.reviews = approve(PE, QA)
    refused(run(ticket), "merge s06/plan first (bootstrap step)")


@pytest.mark.integration
def test_script_bootstrap_ci_fix_passes_without_a_row() -> None:
    stub = GitHubStub()
    stub.pr["head"]["ref"] = "s05/ci-fix-red-main"
    stub.reviews = approve(PE, QA)
    res = run(stub)
    allowed(res)
    assert f"author-role: {SRE}" in res.stdout


@pytest.mark.integration
def test_script_bootstrap_docs_branch_with_a_python_file_fails_closed() -> None:
    stub = GitHubStub(files=changed("docs/x.md", "docs/tool.py"), check_runs=t0_runs())
    stub.pr["head"]["ref"] = "docs/audit-x"
    stub.reviews = approve(PE, QA)
    refused(run(stub), "open an s<nn>/<id> ticket")


@pytest.mark.integration
def test_script_bootstrap_conflicting_row_for_the_plan_fails_closed() -> None:
    stub = GitHubStub(files=changed("docs/sprints/05/kickoff.md"), check_runs=t0_runs())
    stub.pr["head"]["ref"] = "s05/plan"
    stub.contents[(OWNERS_05, "main")] = owners_json([("s05/plan", SRE)])
    stub.reviews = approve(PE)
    refused(run(stub), "s05/plan", "conflict")


@pytest.mark.integration
def test_script_a_role_file_body_edit_is_tier_0_and_a_tools_edit_tier_2() -> None:
    path = ".claude/agents/principal-designer.md"
    base = "---\nname: principal-designer\ntools: Read\n---\nbody\n"
    stub = GitHubStub(files=changed(path), check_runs=t0_runs())
    stub.contents[(path, "b0" * 20)] = base.encode()
    stub.contents[(path, HEAD_SHA)] = (base + "more body\n").encode()
    stub.reviews = approve(PE)
    res = run(stub)
    allowed(res)
    stub.contents[(path, HEAD_SHA)] = base.replace("Read", "Read, Bash").encode()
    refused(run(stub), SEC, "review-tier: 2")


@pytest.mark.integration
def test_script_a_truncated_tree_fails_closed_to_tier_1() -> None:
    stub = GitHubStub(files=changed("docs/process/x.md"), check_runs=t0_runs(), tree_truncated=True)
    stub.reviews = approve("principal-designer")
    refused(run(stub), PE, "review-tier: 1")


@pytest.mark.integration
def test_script_reads_the_owner_file_on_main_only() -> None:
    stub = GitHubStub()
    stub.reviews = approve(PE, QA)
    allowed(run(stub))
    asked = [p for p, _ in stub.requests if "/contents/" in p and "ticket-owners" in p]
    assert asked
    assert all(re.search(r"[?&]ref=main\b", p) for p in asked), asked


# ======================== PRC-2.1 (sprint-05 §7 merge_tiers.feature): unmatched code is tier 2
@pytest.mark.unit
@pytest.mark.parametrize("path", ["newdir/tool.py", "newdir/run.sh", "tool.py"])
def test_an_unmatched_executable_outside_docs_is_tier_2(path: str) -> None:
    rt = _load("review_tiers")
    assert rt.classify([rt.ChangedFile(path)]).tier == 2


@pytest.mark.unit
def test_an_unmatched_shebang_file_under_docs_stays_tier_1() -> None:
    rt = _load("review_tiers")
    assert rt.classify([rt.ChangedFile("docs/tools/run-check", shebang=True)]).tier == 1


# ========== SEC-193-01: the files API caps at 3000 files, so a short read must not lower the tier
def unknown(res: subprocess.CompletedProcess[str], *words: str) -> None:
    assert res.returncode == 2, res.stdout + res.stderr
    assert "merge-ready: unknown" in res.stdout
    for word in words:
        assert word in res.stdout, res.stdout


@pytest.mark.integration
def test_script_exits_2_when_the_files_read_differ_from_changed_files() -> None:
    stub = GitHubStub(files=changed("docs/process/x.md"), check_runs=t0_runs())
    stub.pr["changed_files"] = 3001  # GitHub listed 1 of them; the gate file may be in the rest
    stub.reviews = approve("principal-designer")
    unknown(run(stub), "3001", "1")


@pytest.mark.integration
def test_script_exits_2_when_the_pr_has_3000_files_or_more() -> None:
    paths = [f"docs/bulk/f{i:04d}.md" for i in range(3000)]
    stub = GitHubStub(files=changed(*paths), check_runs=t0_runs(), page_size=100)
    stub.reviews = approve("principal-designer")
    unknown(run(stub), "3000")


@pytest.mark.integration
def test_script_exits_2_when_the_pr_has_no_changed_files_count() -> None:
    stub = GitHubStub(files=changed("docs/process/x.md"), check_runs=t0_runs())
    stub.pr["changed_files"] = None
    stub.reviews = approve("principal-designer")
    unknown(run(stub), "changed_files")
