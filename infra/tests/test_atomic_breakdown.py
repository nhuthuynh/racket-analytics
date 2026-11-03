"""QA-DOR-CHECK unit tests (PRC-7.1, definition-of-ready "Atomic breakdown"): planted rows in a
small breakdown text, one break per rule, negative first; the command-line contract; and the ci.yml
wiring (the check is a step of the draft-skipped `doc-check` job)."""

# ruff: noqa: E501, RUF001  (GOOD mirrors the real breakdown's table rows and characters)
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from atomic_breakdown_fixtures import blank_cell, drop_negative_examples, rename_id, run_check
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

CI = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())

GOOD = """# Sprint NN requirements breakdown (atomic items)

## 1. NFR items

### NFR-010 latency → story ST-074

Common method for .1-.2: Locust at the client, 5 min window, 3 runs.

| Id | Characteristic | Metric and unit | Target | Test level | Scorecard |
|---|---|---|---|---|---|
| NFR-010.1 | latency | p95 ms | ≤ 300 | perf | G-01 |
| NFR-010.2 | latency | p99 ms | ≤ 800 | perf | G-01 |

### NFR-041 availability → story ST-075

Burn-rate multipliers are judgment.

| Id | Characteristic | Metric and unit | Method | Target | Test level | Ticket |
|---|---|---|---|---|---|---|
| NFR-041.3 | fast-burn alert | alert state | promtool rule test | firing on 10 %; not on 0.1 % (negative) | promtool | ST-075c |
| NFR-049.1 | policy text | policy exists | `docs/ops/policy.md` | drafted; **PO acceptance is human (P17)** | doc-check | ST-075c |

### NFR-024 supported clients → story ST-079

Critical journeys: sign-in. Each item = pass rate of those specs in one Playwright project, 3 repeats.

| Id | Browser × form factor | Target | Test level | Scorecard |
|---|---|---|---|---|
| NFR-024.1 | desktop Chrome | 100 % | E2E | G-04 |
| NFR-024.4 | real iOS Safari | 100 % | **human (P20, OQ-17)** | §5 |

### NFR-006 vision accuracy → story ST-084

| Id | Rule or item | Test level | Ticket |
|---|---|---|---|
| NFR-006.1 | A match needs start and end within ±1.0 s (negative: 1.01 s off → no match) | unit | ST-084b |

### NFR-070 legal gate → **human (P16)**, no ticket.

## 2. FR rules

### FR-124 swap → story ST-081

```gherkin
Rule: FR-124.R1 When a player presses "Not for me", the API returns a different drill
  Example: solo player with a wall (happy)
  Example: no other fitting drill → 409 no_alternative (negative)
Rule: FR-124.R2 A swap never returns a drill already in that session
  Example: 3-weakness session (happy)
  Example: the only alternative is already in the session → 409 (negative)
```

## 3. Release and demo items

| Id | Item | Test level | Ticket |
|---|---|---|---|
| REL-1.1 | Release notes list every FR | doc-check | ST-082 |
| USAB-1.1 | Usability kit | doc-check | ST-083 |

## 4. Process items

| Id | Rule (one observable outcome) | Test level | Ticket |
|---|---|---|---|
| PRC-7.1 | The check fails on a non-atomic row | unit + CI | QA-DOR-CHECK |

## 4.1 Carried decisions (no new requirement)

| Item | Ticket |
|---|---|
| TCR rows 11 and 14 decided | QA-TCR-04 |

## 5. Assumptions

| # | Assumption | Default |
|---|---|---|
| A1 | iOS Safari is release-blocking | yes |
"""


def check(tmp_path: Path, text: str) -> tuple[int, str]:
    path = tmp_path / "requirements-breakdown.md"
    path.write_text(text)
    proc = run_check(str(path))
    return proc.returncode, proc.stdout + proc.stderr


def fail_lines(out: str) -> list[str]:
    return [line for line in out.splitlines() if line.startswith("FAIL")]


# ------------------------------------------------------------------ NFR rows (negative first)
@pytest.mark.parametrize(
    ("column", "attribute"),
    [
        ("Metric and unit", "metric"),
        ("Method", "method"),
        ("Target", "target"),
        ("Test level", "test level"),
    ],
)
def test_an_nfr_row_with_an_empty_attribute_cell_fails(
    tmp_path: Path, column: str, attribute: str
) -> None:
    rc, out = check(tmp_path, blank_cell(GOOD, "NFR-041.3", column))
    assert rc == 1, out
    assert fail_lines(out) == [
        f"FAIL nfr: {tmp_path / 'requirements-breakdown.md'}:"
        f"{_line_of(GOOD, '| NFR-041.3 |')}: NFR-041.3 has no {attribute}"
    ], out


def test_a_dash_counts_as_an_empty_cell(tmp_path: Path) -> None:
    text = GOOD.replace(
        "| NFR-010.1 | latency | p95 ms | ≤ 300 |", "| NFR-010.1 | latency | — | ≤ 300 |"
    )
    rc, out = check(tmp_path, text)
    assert rc == 1, out
    assert any("NFR-010.1 has no metric" in line for line in fail_lines(out)), out


def test_an_nfr_table_without_a_method_column_or_section_method_fails(tmp_path: Path) -> None:
    text = GOOD.replace(
        "Common method for .1-.2: Locust at the client, 5 min window, 3 runs.\n", ""
    )
    rc, out = check(tmp_path, text)
    assert rc == 1, out
    assert [line.rsplit(": ", 1)[1] for line in fail_lines(out)] == [
        "NFR-010.1 has no method",
        "NFR-010.2 has no method",
    ], out


def test_a_section_note_that_is_not_a_method_does_not_cover_a_missing_method(
    tmp_path: Path,
) -> None:
    # The NFR-041 section opens with "Burn-rate multipliers are judgment.": not a method line.
    rc, out = check(tmp_path, blank_cell(GOOD, "NFR-041.3", "Method"))
    assert rc == 1, out


def test_a_section_method_does_not_reach_the_next_section(tmp_path: Path) -> None:
    text = GOOD.replace(
        "Burn-rate multipliers are judgment.", "Method for .3: promtool on a synthetic series."
    )
    text = text.replace(
        "Common method for .1-.2: Locust at the client, 5 min window, 3 runs.\n", ""
    )
    rc, out = check(tmp_path, text)
    assert rc == 1, out
    assert any("NFR-010.1 has no method" in line for line in fail_lines(out)), out


def test_an_nfr_table_without_a_test_level_column_fails(tmp_path: Path) -> None:
    text = GOOD.replace(
        "| Id | Rule or item | Test level | Ticket |\n|---|---|---|---|\n"
        "| NFR-006.1 | A match needs start and end within ±1.0 s (negative: 1.01 s off → no match) "
        "| unit | ST-084b |",
        "| Id | Rule or item | Ticket |\n|---|---|---|\n"
        "| NFR-006.1 | A match needs start and end within ±1.0 s (negative: 1.01 s off → no match) "
        "| ST-084b |",
    )
    assert text != GOOD
    rc, out = check(tmp_path, text)
    assert rc == 1, out
    assert any("NFR-006.1 has no test level" in line for line in fail_lines(out)), out


def test_without_each_item_line_a_form_factor_table_has_no_metric_or_method(
    tmp_path: Path,
) -> None:
    text = GOOD.replace(
        " Each item = pass rate of those specs in one Playwright project, 3 repeats.", ""
    )
    rc, out = check(tmp_path, text)
    assert rc == 1, out
    found = {line.rsplit(": ", 1)[1] for line in fail_lines(out)}
    assert {"NFR-024.1 has no metric", "NFR-024.1 has no method"} <= found, out


# ------------------------------------------------------------------ FR rules
def test_an_fr_rule_without_a_negative_example_fails(tmp_path: Path) -> None:
    rc, out = check(tmp_path, drop_negative_examples(GOOD, "FR-124.R2"))
    assert rc == 1, out
    assert [line.rsplit(": ", 1)[1] for line in fail_lines(out)] == [
        "FR-124.R2 has no negative Example"
    ], out


def test_an_fr_rule_with_no_examples_fails(tmp_path: Path) -> None:
    text = GOOD.replace(
        "  Example: solo player with a wall (happy)\n"
        "  Example: no other fitting drill → 409 no_alternative (negative)\n",
        "",
    )
    rc, out = check(tmp_path, text)
    assert rc == 1, out
    assert any("FR-124.R1 has no negative Example" in line for line in fail_lines(out)), out


def test_negative_in_the_rule_line_itself_does_not_count(tmp_path: Path) -> None:
    text = drop_negative_examples(GOOD, "FR-124.R1").replace(
        "Rule: FR-124.R1 When", "Rule: FR-124.R1 (negative) When"
    )
    rc, out = check(tmp_path, text)
    assert rc == 1, out


@pytest.mark.parametrize("bad", ["FR-124.1", "FR124.R1", "FR-12a.R1", "fr-124.R1"])
def test_an_fr_rule_id_outside_the_agreed_format_fails(tmp_path: Path, bad: str) -> None:
    rc, out = check(tmp_path, GOOD.replace("Rule: FR-124.R2 ", f"Rule: {bad} "))
    assert rc == 1, out
    assert any(f"id {bad}" in line for line in fail_lines(out)), out


# ------------------------------------------------------------------ ids
@pytest.mark.parametrize("bad", ["PRC7.1", "PRC-7.x", "VERIFYS-1.1", "prc-7.1", "PRC-"])
def test_an_item_id_the_finding_id_parser_cannot_read_fails(tmp_path: Path, bad: str) -> None:
    rc, out = check(tmp_path, rename_id(GOOD, "PRC-7.1", bad))
    assert rc == 1, out
    assert any(f"id {bad}" in line for line in fail_lines(out)), out


def test_an_nfr_id_with_trailing_text_fails(tmp_path: Path) -> None:
    rc, out = check(tmp_path, rename_id(GOOD, "NFR-010.2", "NFR-010.2b"))
    assert rc == 1, out
    assert any("id NFR-010.2b" in line for line in fail_lines(out)), out


# ------------------------------------------------------------------ the clean file and the CLI
def test_the_planted_clean_breakdown_passes(tmp_path: Path) -> None:
    rc, out = check(tmp_path, GOOD)
    assert rc == 0, out
    assert out.strip().endswith("0 problem(s)"), out


def test_every_problem_is_reported_not_only_the_first(tmp_path: Path) -> None:
    text = drop_negative_examples(blank_cell(GOOD, "NFR-041.3", "Target"), "FR-124.R1")
    rc, out = check(tmp_path, text)
    assert rc == 1, out
    assert len(fail_lines(out)) == 2, out
    assert "2 problem(s)" in out, out


def test_a_missing_file_is_a_usage_error(tmp_path: Path) -> None:
    proc = run_check(str(tmp_path / "nope.md"))
    assert proc.returncode == 2, proc.stdout + proc.stderr


def test_a_breakdown_without_any_item_fails_closed(tmp_path: Path) -> None:
    rc, out = check(tmp_path, "# Empty breakdown\n")
    assert rc == 1, out
    assert "no items" in out, out


def test_without_arguments_it_checks_the_current_sprints_breakdown(tmp_path: Path) -> None:
    sprints = tmp_path / "docs" / "sprints"
    (sprints / "07").mkdir(parents=True)
    (sprints / "sprint-06.md").write_text("# 6\n")
    (sprints / "sprint-07.md").write_text("# 7\n")
    (sprints / "07" / "requirements-breakdown.md").write_text(
        blank_cell(GOOD, "NFR-010.1", "Target")
    )
    proc = run_check("--root", str(tmp_path))
    assert proc.returncode == 1, proc.stdout
    assert "docs/sprints/07/requirements-breakdown.md" in proc.stdout, proc.stdout


def test_without_arguments_and_no_breakdown_yet_it_skips(tmp_path: Path) -> None:
    sprints = tmp_path / "docs" / "sprints"
    sprints.mkdir(parents=True)
    (sprints / "sprint-09.md").write_text("# 9\n")
    proc = run_check("--root", str(tmp_path))
    assert proc.returncode == 0, proc.stdout
    assert "skipped (PRC-7.1)" in proc.stdout, proc.stdout


def test_the_real_current_breakdown_passes() -> None:
    proc = run_check()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "0 problem(s)" in proc.stdout, proc.stdout


# ------------------------------------------------------------------ ci.yml wiring
def test_doc_check_job_runs_the_atomic_breakdown_check_without_arguments() -> None:
    runs = [step.get("run", "") for step in CI["jobs"]["doc-check"]["steps"]]
    assert "python3 scripts/ci/check_atomic_breakdown.py" in [r.strip() for r in runs], runs


def _line_of(text: str, needle: str) -> int:
    return next(i for i, line in enumerate(text.splitlines(), 1) if line.startswith(needle))


# planted helpers stay honest: each one changes the text
@pytest.mark.parametrize(
    "planted",
    [
        lambda: blank_cell(GOOD, "NFR-041.3", "Method"),
        lambda: drop_negative_examples(GOOD, "FR-124.R1"),
        lambda: rename_id(GOOD, "PRC-7.1", "PRC7.1"),
    ],
)
def test_each_planting_helper_changes_the_text(planted) -> None:  # type: ignore[no-untyped-def]
    assert planted() != GOOD
