"""EM-CLOSE-CHECKS (story PRC-05; atomic items PRC-6.1-6.3; goal metric G05-12; retro 4 F1/F3,
L22-L24): the Sprint 5 close checks under `docs/sprints/05/close-checks/`.

- `retro_ready.py` (PRC-6.1) is the RETRO trigger: rc 1 while a VERIFY-05 PR is open, while no
  VERIFY-05 PR is merged, or while any VERIFY-05 finding's latest ledger row is not Fixed.
- `retro05_check.py` (PRC-6.2, PRC-6.3) is the close checklist: the merged Sprint 5 PR set from
  GitHub equals the `status.json` map (set difference printed), every Open blocker row names a
  cause that is still open, and there is at most one RETRO-05 PR.

Unit tests drive the pure functions; integration tests run the scripts over real HTTP against
`close_checks_stub.py`. Negative cases (the planted open VERIFY PR, the planted extra PR, the
planted closed cause) come first. Exit codes: 0 met, 1 not met, 2 unknown (fail closed,
ADR 0014).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from close_checks_stub import REPO, CloseStub, pr, serve
from conftest import REPO_ROOT

CHECKS = REPO_ROOT / "docs" / "sprints" / "05" / "close-checks"
READY = CHECKS / "retro_ready.py"
CLOSE = CHECKS / "retro05_check.py"

VERIFY_MERGED = pr(301, "VERIFY-05", head="s05/verify-05-sprint-5-goal-verification")
VERIFY_OPEN = pr(302, "VERIFY-05-r2", merged=False, head="s05/verify-05-r2-re-measure")

LEDGER_HEAD = (
    "# Sprint 5 review rounds\n\n## VERIFY-05\n\n"
    "| Finding | Severity | Disposition | Owner |\n|---|---|---|---|\n"
)


def ledger(*rows: tuple[str, str, str]) -> str:
    return LEDGER_HEAD + "".join(f"| {i} | {s} | {d} | em |\n" for i, s, d in rows)


BLOCKERS_HEAD = (
    "# Sprint 5 blockers\n\n"
    "| Date | Raised by | Blocker | Impact | Unblock by | Status |\n|---|---|---|---|---|---|\n"
)


def blockers(*rows: tuple[str, str]) -> str:
    return BLOCKERS_HEAD + "".join(f"| 2026-11-12 | em | {b} | x | PO | {s} |\n" for b, s in rows)


def status(*prs: int, merged: bool = True) -> dict[str, Any]:
    return {
        "sprint": 5,
        "ticket_prs": {"map": [{"id": f"T-{n}", "pr": n, "merged": merged} for n in prs]},
    }


def load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------- unit: PRC-6.1 retro trigger


@pytest.mark.unit
def test_a_planted_open_verify_pr_makes_the_retro_not_ready() -> None:
    rr = load(READY)
    problems = rr.verify_problems([VERIFY_MERGED, VERIFY_OPEN], ledger())
    assert any("#302" in p and "open" in p for p in problems), problems


@pytest.mark.unit
def test_no_merged_verify_pr_makes_the_retro_not_ready() -> None:
    rr = load(READY)
    problems = rr.verify_problems([pr(240, "ST-090")], ledger())
    assert any("no merged VERIFY-05 PR" in p for p in problems), problems


@pytest.mark.unit
def test_a_verify_pr_closed_without_a_merge_does_not_count_as_merged() -> None:
    rr = load(READY)
    closed = pr(303, "VERIFY-05", merged=False, state="closed", head="s05/verify-05-x")
    problems = rr.verify_problems([closed], ledger())
    assert any("no merged VERIFY-05 PR" in p for p in problems), problems


@pytest.mark.unit
def test_a_verify_pr_is_found_by_its_branch_even_without_the_title_id() -> None:
    rr = load(READY)
    by_branch = pr(304, "X", merged=False, head="s05/verify-05-r3")
    by_branch["title"] = "docs: verification round 3"
    problems = rr.verify_problems([VERIFY_MERGED, by_branch], ledger())
    assert any("#304" in p for p in problems), problems


@pytest.mark.unit
@pytest.mark.parametrize("disposition", ["Open", "**Open**: re-measure", "Deferred to S6", ""])
def test_a_verify_finding_whose_latest_row_is_not_fixed_makes_the_retro_not_ready(
    disposition: str,
) -> None:
    rr = load(READY)
    text = ledger(("QA-VERIFY05R1-01", "minor", disposition))
    problems = rr.verify_problems([VERIFY_MERGED], text)
    assert any("QA-VERIFY05R1-01" in p for p in problems), problems


@pytest.mark.unit
def test_the_latest_ledger_row_of_a_verify_finding_wins() -> None:
    rr = load(READY)
    text = ledger(
        ("QA-VERIFY05R1-01", "major", "Open"),
        ("QA-VERIFY05R1-01", "major", "**Fixed** (#310, re-measured 2026-11-13)"),
        ("SRE-VERIFY05R2-03", "minor", "Fixed"),
    )
    assert rr.verify_problems([VERIFY_MERGED], text) == []


@pytest.mark.unit
def test_findings_of_other_rounds_and_sprints_are_not_verify_05_findings() -> None:
    rr = load(READY)
    text = ledger(("QA-VERIFY04R5-01", "minor", "Open"), ("SEC-S5-TM-01", "blocker", "Open"))
    assert rr.verify_problems([VERIFY_MERGED], text) == []


# ------------------------------------------------------------- unit: PRC-6.2 PR set


@pytest.mark.unit
def test_a_planted_extra_pr_on_github_is_printed_as_a_set_difference() -> None:
    rc = load(CLOSE)
    problems = rc.set_problems({201, 202, 203}, rc.status_prs(status(201, 202)))
    assert "on GitHub, not in status.json: #203" in problems


@pytest.mark.unit
def test_a_status_pr_that_github_does_not_show_merged_is_printed_as_a_set_difference() -> None:
    rc = load(CLOSE)
    problems = rc.set_problems({201}, rc.status_prs(status(201, 205)))
    assert "in status.json, not merged on GitHub: #205" in problems


@pytest.mark.unit
def test_equal_sets_give_no_problem() -> None:
    rc = load(CLOSE)
    assert rc.set_problems({201, 202}, rc.status_prs(status(202, 201))) == []


@pytest.mark.unit
def test_sprint_set_is_merged_into_main_from_sprint_branches_only() -> None:
    rc = load(CLOSE)
    pulls = [
        pr(201, "A"),
        pr(202, "B", merged=False),  # open
        pr(203, "C", merged=False, state="closed"),  # closed without a merge
        pr(204, "D", base="develop"),
        pr(205, "E", head="docs/res-asb"),  # not a Sprint 5 branch
        pr(206, "F", head="s04/old"),
    ]
    assert rc.sprint_merged(pulls, ["s05/"]) == {201}
    assert rc.sprint_merged(pulls, ["s05/", "docs/"]) == {201, 205}


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad",
    [{}, {"ticket_prs": {}}, {"ticket_prs": {"map": [{"id": "T", "pr": "x", "merged": True}]}}],
)
def test_a_status_file_without_a_readable_map_is_refused(bad: dict[str, Any]) -> None:
    rc = load(CLOSE)
    with pytest.raises(ValueError):
        rc.status_prs(bad)


@pytest.mark.unit
def test_status_entries_marked_not_merged_are_not_in_the_merged_set() -> None:
    rc = load(CLOSE)
    st = status(201)
    st["ticket_prs"]["map"].append({"id": "T-9", "pr": 209, "merged": False})
    assert rc.status_prs(st) == {201}


# ------------------------------------------------------------- unit: PRC-6.3 open causes


def states(**kw: str) -> Any:
    table = {int(k[1:]): v for k, v in kw.items()}

    def state(n: int) -> str:
        return table[n]

    return state


@pytest.mark.unit
def test_a_planted_closed_cause_on_an_open_blocker_row_fails() -> None:
    rc = load(CLOSE)
    rows = rc.open_blocker_rows(blockers(("Flag-on stack. Cause: #150", "Open")))
    problems = rc.cause_problems(rows, states(n150="closed"), ledger())
    assert any("#150" in p and "closed" in p for p in problems), problems


@pytest.mark.unit
def test_an_open_row_with_an_open_cause_passes() -> None:
    rc = load(CLOSE)
    rows = rc.open_blocker_rows(blockers(("Disk. Cause: #151", "**Open** (environment)")))
    assert rc.cause_problems(rows, states(n151="open"), ledger()) == []


@pytest.mark.unit
def test_rows_that_are_not_open_are_not_checked() -> None:
    rc = load(CLOSE)
    rows = rc.open_blocker_rows(blockers(("Old. Cause: #150", "**Fixed** (#162)")))
    assert rows == []


@pytest.mark.unit
def test_an_open_row_that_names_no_cause_fails_closed() -> None:
    rc = load(CLOSE)
    rows = rc.open_blocker_rows(blockers(("Something is stuck (#150 merged)", "Open")))
    problems = rc.cause_problems(rows, states(n150="closed"), ledger())
    assert any("names no cause" in p for p in problems), problems


@pytest.mark.unit
def test_a_ledger_finding_cause_is_open_only_while_its_latest_row_is_open() -> None:
    rc = load(CLOSE)
    led = ledger(("SEC-S5-TM-01", "blocker", "Open"), ("COACH-S5-01", "major", "Fixed (#238)"))
    rows = rc.open_blocker_rows(
        blockers(("Backup. Cause: SEC-S5-TM-01", "Open"), ("Drills. Cause: COACH-S5-01", "Open"))
    )
    problems = rc.cause_problems(rows, states(), led)
    assert len(problems) == 1 and "COACH-S5-01" in problems[0], problems


@pytest.mark.unit
def test_a_ledger_cause_that_the_ledger_does_not_hold_fails_closed() -> None:
    rc = load(CLOSE)
    rows = rc.open_blocker_rows(blockers(("X. Cause: QA-VERIFY05R9-99", "Open")))
    problems = rc.cause_problems(rows, states(), ledger())
    assert any("QA-VERIFY05R9-99" in p and "not in the ledger" in p for p in problems), problems


@pytest.mark.unit
def test_a_po_item_cause_counts_as_open() -> None:
    rc = load(CLOSE)
    rows = rc.open_blocker_rows(blockers(("PO list. Causes: P9, P16, setting 6", "Open")))
    assert rc.cause_problems(rows, states(), ledger()) == []


@pytest.mark.unit
def test_a_blockers_file_without_a_status_table_is_refused() -> None:
    rc = load(CLOSE)
    with pytest.raises(ValueError):
        rc.open_blocker_rows("# Sprint 5 blockers\n\nNo table here.\n")


# ------------------------------------------------------------- unit: one close (G05-12)


@pytest.mark.unit
def test_a_second_retro_pr_fails_the_one_close_rule() -> None:
    rc = load(CLOSE)
    pulls = [
        pr(320, "RETRO-05", head="s05/retro-05"),
        pr(330, "RETRO-05", merged=False, head="s05/retro-05-second-close"),
        pr(331, "RETRO-05", merged=False, state="closed", head="s05/retro-05-abandoned"),
    ]
    problems = rc.retro_pr_problems(pulls, "s05/retro-05")
    assert any("#320" in p and "#330" in p for p in problems), problems
    assert rc.retro_pr_problems(pulls[:1], "s05/retro-05") == []


# ------------------------------------------------------------- integration: the scripts


def run(script: Path, stub: CloseStub, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in {"GITHUB_TOKEN", "GH_TOKEN"}}
    env["GITHUB_API_URL"] = stub.url or "http://127.0.0.1:9"
    return subprocess.run(
        [sys.executable, str(script), "--repo", REPO, *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def write(tmp_path: Path, name: str, text: str) -> str:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def close_args(tmp_path: Path, st: dict[str, Any], led: str, bl: str) -> list[str]:
    return [
        "--status",
        write(tmp_path, "status.json", json.dumps(st)),
        "--ledger",
        write(tmp_path, "review-rounds.md", led),
        "--blockers",
        write(tmp_path, "blockers.md", bl),
    ]


@pytest.mark.integration
def test_retro_ready_exits_1_on_a_planted_open_verify_pr(tmp_path: Path) -> None:
    stub = CloseStub(pulls=[VERIFY_MERGED, pr(240, "ST-090"), VERIFY_OPEN])
    with serve(stub):
        r = run(READY, stub, "--ledger", write(tmp_path, "l.md", ledger()))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "retro-ready: not ready" in r.stdout
    assert "#302" in r.stdout
    assert all(q.startswith(f"/repos/{REPO}/") for q in stub.requests), stub.requests
    assert any("page=2" in q for q in stub.requests), stub.requests


@pytest.mark.integration
def test_retro_ready_exits_0_when_verify_is_merged_and_its_findings_fixed(tmp_path: Path) -> None:
    stub = CloseStub(pulls=[VERIFY_MERGED])
    text = ledger(("QA-VERIFY05R1-01", "major", "Fixed (#305)"))
    with serve(stub):
        r = run(READY, stub, "--ledger", write(tmp_path, "l.md", text))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "retro-ready: ready" in r.stdout


@pytest.mark.integration
def test_retro_ready_exits_2_when_github_or_the_ledger_cannot_be_read(tmp_path: Path) -> None:
    stub = CloseStub(fail_status=500)
    with serve(stub):
        r = run(READY, stub, "--ledger", write(tmp_path, "l.md", ledger()))
    assert r.returncode == 2, r.stdout + r.stderr
    assert "retro-ready: unknown" in r.stdout
    with serve(CloseStub()) as ok:
        r = run(READY, ok, "--ledger", str(tmp_path / "missing.md"))
    assert r.returncode == 2, r.stdout + r.stderr


@pytest.mark.integration
def test_retro05_check_exits_1_on_a_planted_extra_pr_and_a_planted_closed_cause(
    tmp_path: Path,
) -> None:
    stub = CloseStub(pulls=[pr(201, "A"), pr(202, "B"), pr(203, "C")], issues={150: "closed"})
    args = close_args(
        tmp_path, status(201, 202), ledger(), blockers(("Stack. Cause: #150", "Open"))
    )
    with serve(stub):
        r = run(CLOSE, stub, *args)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "on GitHub, not in status.json: #203" in r.stdout
    assert "#150" in r.stdout
    assert "retro05-check: not met" in r.stdout
    assert all(q.startswith(f"/repos/{REPO}/") for q in stub.requests), stub.requests


@pytest.mark.integration
def test_retro05_check_exits_0_when_the_close_is_consistent(tmp_path: Path) -> None:
    stub = CloseStub(pulls=[pr(201, "A"), pr(202, "B")], issues={151: "open"})
    args = close_args(
        tmp_path, status(201, 202), ledger(), blockers(("Disk. Cause: #151", "Open"))
    )
    with serve(stub):
        r = run(CLOSE, stub, *args)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "retro05-check: met" in r.stdout


@pytest.mark.integration
def test_retro05_check_exits_2_when_github_cannot_be_read_or_status_is_bad(
    tmp_path: Path,
) -> None:
    stub = CloseStub(fail_status=500)
    with serve(stub):
        r = run(CLOSE, stub, *close_args(tmp_path, status(201), ledger(), blockers()))
    assert r.returncode == 2, r.stdout + r.stderr
    assert "retro05-check: unknown" in r.stdout
    with serve(CloseStub(pulls=[pr(201, "A")])) as ok:
        r = run(CLOSE, ok, *close_args(tmp_path, {"sprint": 5}, ledger(), blockers()))
    assert r.returncode == 2, r.stdout + r.stderr
