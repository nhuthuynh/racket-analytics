"""ST-082 unit tests for scripts/ci/check_release_notes.py (REL-1.1, FR-055.R1): a small matrix,
env file and notes text, one planted break per rule, negative first; the command-line contract;
and the ci.yml wiring (the check is a step of the draft-skipped `doc-check` job)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT
from release_notes_fixtures import (
    drop_notice,
    drop_row,
    run_check,
    set_flag_default,
    strip_pn,
)

pytestmark = pytest.mark.unit

MATRIX = """# Traceability

| FR | Title | Priority | Release | Status | Epic | Sprint | Test levels |
|---|---|---|---|---|---|---|---|
| FR-001 | Passwordless sign-in | Must | R1 | ready-candidate | E1 | S1 | U |
| FR-025 | Footage quality report | Should | R1 (fps); R2 (court) | ready-candidate | E2 | S0 | U |
| FR-026 | Analysis level | Should | R2 | ready-candidate | E2 | S6 | U |
| FR-081 | Normalise | Must | R1/R2 | ready-candidate | E3 | S0 | U |
"""

ENV = """# flags
DEV_IDENTITY_ENABLED=true
FEATURE_AGE_GATE=false
FEATURE_QUOTAS=false
AGE_MINIMUM=18
"""

GOOD = """---
release: r1-rc1
alembic_revision: "0021"
previous_release: r1-rehearsal-0020
previous_ref: 09d279ddb42563bfd014a26d74e84db30c90e237
previous_alembic_revision: "0020"
---
# R1 release notes

> **Notice:** scores are **unofficial scoring (rules not yet verified)** (P7).

## Features

| FR | Title | In this release |
|---|---|---|
| FR-001 | Passwordless sign-in | shipped |
| FR-025 | Footage quality report | shipped (fps only) |
| FR-081 | Normalise | probe only |

## Flags

| Flag | Default | What it turns on | Waits on |
|---|---|---|---|
| `FEATURE_AGE_GATE` | `false` | age confirmation | P16 |
| `FEATURE_QUOTAS` | `false` | quotas | P8 |

## Known limitations

| Id | Limitation | Waits on |
|---|---|---|
| L-1 | Scoring follows provisional values | P7 |
| L-2 | Drills are not reviewed by a human coach | P15 |
"""


def _run(tmp_path: Path, notes: str, matrix: str = MATRIX, env: str = ENV):
    (tmp_path / "notes.md").write_text(notes)
    (tmp_path / "matrix.md").write_text(matrix)
    (tmp_path / "env.example").write_text(env)
    return run_check(
        "--notes",
        str(tmp_path / "notes.md"),
        "--matrix",
        str(tmp_path / "matrix.md"),
        "--env",
        str(tmp_path / "env.example"),
    )


def _fails(proc, *words: str) -> list[str]:
    out = proc.stdout + proc.stderr
    assert proc.returncode == 1, out
    lines = [ln for ln in out.splitlines() if ln.startswith("FAIL")]
    assert lines, out
    for word in words:
        assert any(word in ln for ln in lines), out
    return lines


# ------------------------------------------------------------------ FR-055.R1: the notice
def test_notes_without_the_unofficial_scoring_notice_fail(tmp_path: Path) -> None:
    _fails(_run(tmp_path, drop_notice(GOOD)), "unofficial scoring")


def test_a_notice_only_inside_a_later_section_does_not_count(tmp_path: Path) -> None:
    moved = drop_notice(GOOD).replace("## Flags", "## Flags\n\nThis is unofficial scoring.\n")
    _fails(_run(tmp_path, moved), "unofficial scoring")


# ------------------------------------------------------------------ REL-1.1: FRs
def test_an_r1_fr_missing_from_the_features_table_fails(tmp_path: Path) -> None:
    _fails(_run(tmp_path, drop_row(GOOD, "FR-001")), "FR-001")


def test_an_fr_whose_release_starts_with_r1_counts_as_r1(tmp_path: Path) -> None:
    lines = _fails(_run(tmp_path, drop_row(drop_row(GOOD, "FR-025"), "FR-081")), "FR-025")
    assert any("FR-081" in ln for ln in lines)


def test_an_r2_only_fr_is_not_required(tmp_path: Path) -> None:
    proc = _run(tmp_path, GOOD)
    assert "FR-026" not in proc.stdout


def test_a_matrix_without_r1_rows_is_a_usage_error(tmp_path: Path) -> None:
    proc = _run(tmp_path, GOOD, matrix="# empty\n")
    assert proc.returncode == 2, proc.stdout + proc.stderr


# ------------------------------------------------------------------ REL-1.1: flags
def test_a_flag_missing_from_the_flags_table_fails(tmp_path: Path) -> None:
    _fails(_run(tmp_path, drop_row(GOOD, "FEATURE_AGE_GATE")), "FEATURE_AGE_GATE")


def test_a_flag_with_the_wrong_default_fails(tmp_path: Path) -> None:
    _fails(_run(tmp_path, set_flag_default(GOOD, "FEATURE_QUOTAS", "true")), "FEATURE_QUOTAS")


def test_only_feature_variables_are_flags(tmp_path: Path) -> None:
    proc = _run(tmp_path, GOOD)
    assert "DEV_IDENTITY_ENABLED" not in proc.stdout
    assert "AGE_MINIMUM" not in proc.stdout


# ------------------------------------------------------------------ REL-1.1: limitations
def test_a_limitation_without_a_p_n_fails(tmp_path: Path) -> None:
    _fails(_run(tmp_path, strip_pn(GOOD, "L-1")), "L-1")


def test_notes_without_any_known_limitation_fail(tmp_path: Path) -> None:
    text = drop_row(drop_row(GOOD, "L-1"), "L-2")
    _fails(_run(tmp_path, text), "limitation")


# ------------------------------------------------------------------ front matter (ADR 0058 rule 7)
@pytest.mark.parametrize("key", ["release", "alembic_revision", "previous_alembic_revision"])
def test_front_matter_without_a_rollback_key_fails(tmp_path: Path, key: str) -> None:
    text = "\n".join(ln for ln in GOOD.splitlines() if not ln.startswith(f"{key}:")) + "\n"
    _fails(_run(tmp_path, text), key)


def test_broken_front_matter_fails(tmp_path: Path) -> None:
    _fails(_run(tmp_path, GOOD.replace("release: r1-rc1", "release: [r1")), "front matter")


# ------------------------------------------------------------------ happy path and contract
def test_good_notes_pass(tmp_path: Path) -> None:
    proc = _run(tmp_path, GOOD)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "0 problem(s)" in proc.stdout


def test_the_real_r1_notes_pass_against_the_real_register_and_flags() -> None:
    proc = run_check()
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_a_missing_notes_file_is_a_usage_error(tmp_path: Path) -> None:
    proc = run_check("--notes", str(tmp_path / "nope.md"))
    assert proc.returncode == 2


def test_the_check_is_a_step_of_the_doc_check_job() -> None:
    ci = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())
    runs = [s.get("run", "") for s in ci["jobs"]["doc-check"]["steps"]]
    assert any(r.strip() == "python3 scripts/ci/check_release_notes.py" for r in runs), runs
