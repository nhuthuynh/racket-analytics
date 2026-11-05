"""ST-078a unit tests for docs/security/tools/asvs_status.py, negative cases first.

The tool is the G05-07 method (NFR-050.1, .4, .5): an applicable L1/L2 row (or an adopted L3
row) must be ``Pass`` or ``Fail``; a ``Fail`` row must name a fix ticket id or a residual-risk
owner (``P19`` or an ADR id); a ``Pass`` row must name an evidence command or a test id. Any
other status, including the Sprint 0 planning statuses, counts as not assessed (fail closed).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

TOOL = REPO_ROOT / "docs" / "security" / "tools" / "asvs_status.py"

_spec = importlib.util.spec_from_file_location("asvs_status", TOOL)
assert _spec
assert _spec.loader
asvs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(asvs)

HEAD = (
    "| ID | L | Requirement (abridged) | Applies | Status | Owner / story | Verification |\n"
    "|---|---|---|---|---|---|---|\n"
)
ALL_RULES = ("not-assessed", "fail-without-owner", "pass-without-evidence")


def _doc(**chapters: list[str]) -> str:
    out = "# planted\n\n## Checklist\n\n"
    for chapter, rows in chapters.items():
        out += f"### {chapter} Title of {chapter}\n\nProse line.\n\n{HEAD}"
        out += "".join(r + "\n" for r in rows) + "\n"
    return out


def _row(rid: str, status: str, owner: str = "security", ver: str = "—", *, applies: str = "Yes",
         level: str = "2") -> str:  # fmt: skip
    return f"| {rid} | {level} | requirement text | {applies} | {status} | {owner} | {ver} |"


def _problems(text: str, **kw: object) -> list[str]:
    rows = asvs.select(asvs.parse_rows(text), level=kw.get("level", 2),
                       chapters=kw.get("chapters"))  # fmt: skip
    return [p.line() for p in asvs.problems(rows, kw.get("rules", ALL_RULES))]


# ---------------------------------------------------------------- not assessed (NFR-050.1)
def test_planted_not_assessed_row_fails():
    assert _problems(_doc(V1=[_row("1.1.1", "Not assessed")])) == [
        "FAIL not-assessed: 1.1.1 (V1) status 'Not assessed'"
    ]


@pytest.mark.parametrize("status", ["S0 planned", "S1", "Later (first deploy)", "Open (F-3)", ""])
def test_planning_statuses_count_as_not_assessed(status: str):
    assert _problems(_doc(V2=[_row("2.4.1", status)])) == [
        f"FAIL not-assessed: 2.4.1 (V2) status '{status}'"
    ]


def test_na_status_on_an_applicable_row_is_not_assessed():
    assert _problems(_doc(V4=[_row("4.1.1", "N/A", applies="Yes")])) == [
        "FAIL not-assessed: 4.1.1 (V4) status 'N/A' but Applies is 'Yes'"
    ]


def test_a_row_whose_applies_is_still_tbd_is_not_assessed_even_with_a_pass():
    ver = "`grep -rn eval backend/src` → none"
    assert _problems(_doc(V1=[_row("1.3.2", "Pass", ver=ver, applies="TBD")])) == [
        "FAIL not-assessed: 1.3.2 (V1) Applies is 'TBD'"
    ]


def test_a_not_applicable_row_with_status_na_is_assessed():
    assert _problems(_doc(V4=[_row("4.3.1", "N/A", "—", "no GraphQL", applies="N/A")])) == []


# ---------------------------------------------------------- Fail without owner (NFR-050.4)
@pytest.mark.parametrize("owner", ["security", "—", "", "BE", "F-3", "NFR-050"])
def test_planted_fail_without_owner_fails(owner: str):
    assert _problems(_doc(V5=[_row("5.4.3", "Fail", owner)])) == [
        "FAIL fail-without-owner: 5.4.3 (V5) names no fix ticket id or residual-risk owner"
        " (P-n or ADR id)"
    ]


@pytest.mark.parametrize(
    "owner", ["ST-078d", "BE ST-078d", "QA-VERIFY04R5-01", "SEC-5", "P19 (residual)", "ADR 0059"]
)
def test_a_fail_with_a_ticket_or_residual_owner_passes(owner: str):
    assert _problems(_doc(V5=[_row("5.4.3", "Fail", owner)])) == []


# -------------------------------------------------------- Pass without evidence (NFR-050.5)
@pytest.mark.parametrize(
    "ver", ["—", "", "code review", "SQLAlchemy bound parameters only", "`racket.platform`"]
)
def test_planted_pass_without_evidence_fails(ver: str):
    assert _problems(_doc(V3=[_row("3.3.4", "Pass", ver=ver)])) == [
        "FAIL pass-without-evidence: 3.3.4 (V3) names no evidence command or test id"
    ]


@pytest.mark.parametrize(
    "ver",
    [
        "`test_outside_test_the_cookie_meets_the_host_prefix_rules`",
        "`backend/tests/integration/test_it_00_14_security_headers.py`",
        "`web/e2e/security-headers.spec.ts`",
        "`tests/features/asvs_status.feature`",
        "`test_probe.py::test_a_probe_gets_only_the_fixed_argv`",
        "IT-00-14",
        "`grep -rn dangerouslySetInnerHTML web/src` → none",
        "`uv run pytest -q tests/regression/test_bola_matrix.py`",
    ],
)
def test_a_pass_with_a_command_or_test_id_passes(ver: str):
    assert _problems(_doc(V3=[_row("3.3.4", "Pass", ver=ver)])) == []


# ------------------------------------------------------------------------- scope and rules
def test_rules_not_asked_for_are_not_reported():
    text = _doc(V1=[_row("1.1.1", "Not assessed"), _row("1.1.2", "Fail")])
    assert _problems(text, rules=("fail-without-owner",)) == [
        "FAIL fail-without-owner: 1.1.2 (V1) names no fix ticket id or residual-risk owner"
        " (P-n or ADR id)"
    ]


def test_level_3_rows_are_out_of_scope_at_level_2_unless_adopted():
    text = _doc(V5=[_row("5.2.5", "Not assessed", level="3"),
                    _row("5.2.4", "Not assessed", level="3 (L3 adopted)")])  # fmt: skip
    assert _problems(text) == ["FAIL not-assessed: 5.2.4 (V5) status 'Not assessed'"]


def test_chapter_range_selects_only_those_chapters():
    text = _doc(V1=[_row("1.1.1", "Not assessed")], V6=[_row("6.1.2", "Not assessed")],
                V12=[_row("12.1.1", "Not assessed")])  # fmt: skip
    assert _problems(text, chapters=asvs.parse_chapters("V1-V5")) == [
        "FAIL not-assessed: 1.1.1 (V1) status 'Not assessed'"
    ]
    assert asvs.parse_chapters("V1-V3,V12") == {"V1", "V2", "V3", "V12"}


@pytest.mark.parametrize("spec", ["V5-V1", "X1", "V0", "V18", "V1-"])
def test_a_bad_chapter_spec_is_refused(spec: str):
    with pytest.raises(ValueError, match="bad chapter spec"):
        asvs.parse_chapters(spec)


def test_counts_per_chapter():
    text = _doc(
        V1=[_row("1.1.1", "Pass", ver="IT-00-14"), _row("1.2.6", "N/A", applies="N/A"),
            _row("1.3.1", "Not assessed")],
        V2=[_row("2.4.1", "Fail", "ST-078d")],
    )  # fmt: skip
    assert asvs.counts(asvs.select(asvs.parse_rows(text), level=2, chapters=None)) == {
        "V1": {"rows": 3, "Pass": 1, "Fail": 0, "N/A": 1, "Not assessed": 1},
        "V2": {"rows": 1, "Pass": 0, "Fail": 1, "N/A": 0, "Not assessed": 0},
    }


# ---------------------------------------------------------------------------------- CLI
def _main(tmp_path: Path, text: str, *args: str) -> int:
    f = tmp_path / "c.md"
    f.write_text(text, encoding="utf-8")
    return asvs.main([str(f), "--level", "2", *args])


def test_cli_exit_1_and_json_report_on_a_problem(tmp_path: Path, capsys):
    out = tmp_path / "reports" / "asvs.json"
    rc = _main(tmp_path, _doc(V1=[_row("1.1.1", "Not assessed")]), "--json", str(out))
    assert rc == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["ok"] is False
    assert report["chapters"]["V1"]["Not assessed"] == 1
    assert report["problems"] == [
        {"rule": "not-assessed", "id": "1.1.1", "chapter": "V1",
         "line": "FAIL not-assessed: 1.1.1 (V1) status 'Not assessed'"}
    ]  # fmt: skip
    assert "| V1 | 1 | 0 | 0 | 0 | 1 |" in capsys.readouterr().out


def test_cli_exit_0_on_a_clean_checklist(tmp_path: Path, capsys):
    assert _main(tmp_path, _doc(V1=[_row("1.1.1", "Pass", ver="IT-00-14")])) == 0
    assert "0 problem(s)" in capsys.readouterr().out


def test_cli_exit_2_when_the_file_is_missing(tmp_path: Path):
    assert asvs.main([str(tmp_path / "nope.md")]) == 2


def test_cli_exit_2_when_no_row_is_in_scope(tmp_path: Path, capsys):
    # Never pass empty: a filter that selects nothing is a usage error, not a clean review.
    assert _main(tmp_path, _doc(V1=[_row("1.1.1", "Pass", ver="IT-00-14")]),
                 "--chapters", "V6") == 2  # fmt: skip
    assert "no checklist row in scope" in capsys.readouterr().out


def test_cli_exit_2_on_an_unknown_rule(tmp_path: Path):
    assert _main(tmp_path, _doc(V1=[_row("1.1.1", "Pass", ver="IT-00-14")]),
                 "--fail-on", "not-assessed,typo") == 2  # fmt: skip


def test_the_real_checklist_parses_all_17_chapters():
    rows = asvs.parse_rows((REPO_ROOT / "docs" / "security" / "asvs-l2-checklist.md").read_text())
    assert {r.chapter for r in rows} == {f"V{n}" for n in range(1, 18)}
    assert len(rows) == 256
