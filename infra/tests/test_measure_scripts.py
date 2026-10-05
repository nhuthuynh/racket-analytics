"""Goal-scorecard measurement harness (docs/sprints/01/goal-scorecard.md, PO standing rule).

The pure helpers in scripts/measure/measurelib.py turn raw live-stack observations into the
numbers the scorecard compares with its targets. Negative cases first: an empty or
unmatched input must never read as a pass (fail closed, ADR 0014).
"""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit

MEASURE = SCRIPTS_DIR / "measure"


def _load():
    spec = importlib.util.spec_from_file_location("measurelib", MEASURE / "measurelib.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["measurelib"] = module
    spec.loader.exec_module(module)
    return module


m = _load()


# ================================================================ percentile
def test_percentile_of_no_samples_is_refused() -> None:
    with pytest.raises(ValueError, match="no samples"):
        m.percentile([], 95)


@pytest.mark.parametrize("p", [-1, 0, 101])
def test_percentile_outside_1_to_100_is_refused(p: float) -> None:
    with pytest.raises(ValueError, match="p must be"):
        m.percentile([1.0], p)


def test_percentile_is_nearest_rank() -> None:
    samples = list(range(1, 101))  # 1..100
    assert m.percentile(samples, 50) == 50
    assert m.percentile(samples, 95) == 95
    assert m.percentile(samples, 99) == 99
    assert m.percentile(samples, 100) == 100
    assert m.percentile([7.0, 3.0, 5.0], 95) == 7.0  # unsorted input


# ================================================================ latency summary
def test_latency_summary_with_no_successful_request_fails_closed() -> None:
    summary = m.latency_summary([], statuses=[500, 502], wall_s=1.0)
    assert summary["p95_ms"] is None
    assert summary["availability"] == 0.0


def test_latency_summary_counts_5xx_against_availability_but_not_429() -> None:
    summary = m.latency_summary([10.0, 20.0, 30.0, 40.0], statuses=[200, 200, 429, 503], wall_s=2.0)
    assert summary["requests"] == 4
    assert summary["status_5xx"] == 1
    assert summary["status_429"] == 1
    # NFR-041: non-5xx / all, excluding 429 -> 2 of 3
    assert summary["availability"] == pytest.approx(2 / 3)
    assert summary["achieved_rps"] == pytest.approx(2.0)
    assert summary["status_unexpected"] == 0
    assert summary["p95_ms"] == 40.0


def test_latency_summary_counts_4xx_other_than_429_as_unexpected() -> None:
    # A 401 or 404 is fast but proves nothing about the read path; the run must not pass.
    summary = m.latency_summary([5.0, 6.0], statuses=[200, 401], wall_s=1.0)
    assert summary["status_unexpected"] == 1


# ================================================================ throughput
@pytest.mark.parametrize("seconds", [0, -1])
def test_throughput_with_no_elapsed_time_is_refused(seconds: float) -> None:
    with pytest.raises(ValueError, match="positive"):
        m.throughput_mbps(1_000_000, seconds)


def test_throughput_is_megabits_per_second() -> None:
    assert m.throughput_mbps(125_000_000, 10.0) == pytest.approx(100.0)


# ================================================================ chunk plan
@pytest.mark.parametrize(("length", "size"), [(-1, 8), (10, 0)])
def test_chunk_plan_rejects_bad_input(length: int, size: int) -> None:
    with pytest.raises(ValueError, match="bad length"):
        m.chunk_plan(length, size)


def test_chunk_plan_covers_the_file_exactly_once() -> None:
    assert m.chunk_plan(0, 4) == []
    assert m.chunk_plan(10, 4) == [(0, 4), (4, 4), (8, 2)]
    assert m.chunk_plan(10, 4, start=4) == [(4, 4), (8, 2)]


def test_effective_chunk_splits_a_small_file_so_the_drop_lands_mid_upload() -> None:
    with pytest.raises(ValueError, match="bad length"):
        m.effective_chunk(0, 8)
    assert m.effective_chunk(1_000, 8 * 1024 * 1024) == 200  # 5 chunks at least
    assert m.effective_chunk(1_000_000_000, 8 * 1024 * 1024) == 8 * 1024 * 1024


# ================================================================ tus headers
def test_tus_metadata_and_checksum_headers() -> None:
    meta = m.tus_metadata(filename="a.mp4")
    assert meta == "filename " + base64.b64encode(b"a.mp4").decode()
    digest = base64.b64encode(hashlib.sha256(b"abc").digest()).decode()
    assert m.checksum_header(b"abc") == f"sha256 {digest}"


# ================================================================ sign-in link
def test_token_from_an_email_without_a_link_is_none() -> None:
    assert m.token_from("Hello, no link here") is None


def test_token_from_the_emailed_link() -> None:
    token = "A" * 43
    body = f"Sign in: https://localhost:3000/auth/callback#token={token}\n"
    assert m.token_from(body) == token


def test_session_cookie_from_set_cookie_headers() -> None:
    assert m.session_cookie([]) is None
    headers = ["other=1; Path=/", "__Host-racket_session=abc_DEF-1; HttpOnly; Secure; Path=/"]
    assert m.session_cookie(headers) == "__Host-racket_session=abc_DEF-1"


# ================================================================ JUnit pass rate
JUNIT = """<?xml version="1.0"?>
<testsuites>
 <testsuite name="pytest">
  <testcase classname="tests.integration.test_it_01_01_magic_link" name="test_a"/>
  <testcase classname="tests.integration.test_it_01_01_magic_link" name="test_b">
   <failure message="boom"/>
  </testcase>
  <testcase classname="tests.integration.test_it_01_04_no_store" name="test_c">
   <skipped message="needs Mailpit"/>
  </testcase>
  <testcase classname="tests.integration.test_it_00_01_matches_api" name="test_d"/>
 </testsuite>
</testsuites>
"""


def _xml(tmp_path: Path, text: str = JUNIT) -> Path:
    path = tmp_path / "junit.xml"
    path.write_text(text, encoding="utf-8")
    return path


def test_junit_rate_with_nothing_selected_fails_closed(tmp_path: Path) -> None:
    result = m.junit_rate([_xml(tmp_path)], include=r"it_09_")
    assert result["selected"] == 0
    assert result["rate"] is None
    assert result["ok"] is False


def test_junit_rate_counts_skips_as_not_passed_by_default(tmp_path: Path) -> None:
    result = m.junit_rate([_xml(tmp_path)], include=r"test_it_01_")
    assert (result["selected"], result["passed"], result["failed"], result["skipped"]) == (
        3,
        1,
        1,
        1,
    )
    assert result["rate"] == pytest.approx(1 / 3)
    assert result["ok"] is False


def test_junit_rate_reports_required_ids_with_no_test(tmp_path: Path) -> None:
    result = m.junit_rate([_xml(tmp_path)], include=r"test_it_0", require=["it_01_01", "it_01_13"])
    assert result["missing"] == ["it_01_13"]
    assert result["ok"] is False


def test_junit_rate_all_passed_is_ok(tmp_path: Path) -> None:
    result = m.junit_rate([_xml(tmp_path)], include=r"test_it_00_", require=["it_00_01"])
    assert result["rate"] == 1.0
    assert result["ok"] is True


def test_junit_rate_cli_exit_code_follows_ok(tmp_path: Path) -> None:
    path = _xml(tmp_path)
    out = tmp_path / "rate.json"
    bad = subprocess.run(
        [
            sys.executable,
            str(MEASURE / "junit_rate.py"),
            "--include",
            "test_it_01_",
            "--json",
            str(out),
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert bad.returncode == 1, bad.stderr
    assert json.loads(out.read_text())["failed"] == 1
    good = subprocess.run(
        [sys.executable, str(MEASURE / "junit_rate.py"), "--include", "test_it_00_", str(path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert good.returncode == 0, good.stderr
    assert json.loads(good.stdout)["rate"] == 1.0


def test_live_scripts_print_help_without_a_stack() -> None:
    for script in ("live_goal.py", "api_latency.py"):
        res = subprocess.run(
            [sys.executable, str(MEASURE / script), "--help"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert res.returncode == 0, (script, res.stderr)
        assert "--api" in res.stdout


# ================================================================ open defects (G01-11)
# QA-V1-07: the scorecard's awk matched /blocking|major/ (the tables say "blocker" or
# "**blocker**") and read column 4 even where the disposition is in another column.
_ROUND_A = """
| Finding | Severity | Disposition | Owner | Evidence |
|---|---|---|---|---|
| PE-R3-05 / QA-R3-05 | blocker | Open, escalated: no CI | PO | runs |
| PE-R3-01 | major | Open, escalated: 429 first | BE | test |
| QA-R3-04 | major | **Fixed** at close | EM | json |
| PE-R3-06 | minor | Open: not fixed yet | QA | — |
| PE-R3-07 | major | Deferred to Sprint 2 | PE | — |
"""

_ROUND_B = """
| Finding | Severity | State at close (EM check) | Owner | Disposition |
|---|---|---|---|---|
| PD-R1-02 | **blocker** | Not re-verified: WebKit captions | FE | Open, escalated (with S-09) |
| PD-R1-08 | minor | Re-raised as PD-R3-04 | FE | See PD-R3-04 |
"""


def test_open_defects_refuses_text_without_a_review_table() -> None:
    with pytest.raises(ValueError, match="no review table"):
        m.open_defects("# Review rounds\n\nNothing here.\n")


def test_open_defects_counts_bold_blocker_rows() -> None:
    rows = m.open_defects(_ROUND_B)
    assert [r["ids"] for r in rows] == [["PD-R1-02"]]
    assert rows[0]["severity"] == "blocker"


def test_open_defects_reads_the_disposition_column_not_column_4() -> None:
    # State says "Not re-verified", Disposition says "Open": the Disposition column decides.
    assert len(m.open_defects(_ROUND_B)) == 1
    closed_by_disposition = _ROUND_B.replace("Open, escalated (with S-09)", "Fixed")
    assert m.open_defects(closed_by_disposition) == []


def test_open_defects_skips_fixed_deferred_and_minor_rows() -> None:
    rows = m.open_defects(_ROUND_A)
    assert [r["ids"] for r in rows] == [["PE-R3-05", "QA-R3-05"], ["PE-R3-01"]]


def test_open_defects_latest_row_wins() -> None:
    later = """
| Finding | Severity | Fix | Files | Evidence |
|---|---|---|---|---|
| PE-R3-01 | major | Fixed. Red first, then green | a.py | 1 passed |
"""
    rows = m.open_defects(_ROUND_A + later)
    assert [r["ids"] for r in rows] == [["PE-R3-05", "QA-R3-05"]]


def test_open_defects_fails_closed_on_partly_and_not_fixed() -> None:
    text = """
| Finding | Severity | Fix summary | Files | Evidence |
|---|---|---|---|---|
| QA-R2-02 | blocker | Partly fixed: records only | a | b |
| PE-R1-S1-02 | blocker | Not fixed: needs a verifier run | a | b |
| QA-V1-05 | major | Fixed. Method corrected | a | b |
"""
    assert [r["ids"] for r in m.open_defects(text)] == [["QA-R2-02"], ["PE-R1-S1-02"]]


def test_open_defects_cli_exit_code_follows_count(tmp_path: Path) -> None:
    path = tmp_path / "review-rounds.md"
    path.write_text(_ROUND_A, encoding="utf-8")
    script = str(MEASURE / "open_defects.py")
    bad = subprocess.run(
        [sys.executable, script, str(path)], capture_output=True, text=True, check=False, timeout=30
    )
    assert bad.returncode == 1, bad.stderr
    assert json.loads(bad.stdout)["open"] == 2
    path.write_text(_ROUND_A.replace("Open, escalated", "Fixed"), encoding="utf-8")
    good = subprocess.run(
        [sys.executable, script, str(path)], capture_output=True, text=True, check=False, timeout=30
    )
    assert good.returncode == 0, good.stderr
    assert json.loads(good.stdout)["open"] == 0


# PE-R2-S1-02: ids that are not XX-R1-01 shaped (S-07, BLK-ASVS-6.3.3) were dropped silently,
# and a finding named in a combined row and again in a single row was counted twice.
def test_open_defects_refuses_a_severity_row_without_a_parsable_id() -> None:
    text = """
| Finding | Severity | Disposition | Files | Evidence |
|---|---|---|---|---|
| the upload flake | major | Not fixed: needs input | a | b |
"""
    with pytest.raises(ValueError, match="no finding id"):
        m.open_defects(text)


def test_open_defects_counts_short_and_dotted_ids() -> None:
    text = """
| Finding | Severity | Disposition | Files | Evidence |
|---|---|---|---|---|
| S-07 | major | Not fixed: needs phone recordings | none | red |
| S-08 | major | Not fixed: depends on CI | none | red |
| BLK-ASVS-6.3.3 | major | Not fixed: needs the PO | none | adr |
| QA-R2V-01 | blocker | Open, escalated | none | runs |
| S-09 | blocker | Fixed | none | green |
"""
    rows = m.open_defects(text)
    assert [r["ids"] for r in rows] == [["S-07"], ["S-08"], ["BLK-ASVS-6.3.3"], ["QA-R2V-01"]]


def test_open_defects_counts_a_finding_in_a_combined_and_a_single_row_once() -> None:
    text = """
| Finding | Severity | Disposition | Files | Evidence |
|---|---|---|---|---|
| PE-R3-05 / QA-R3-05 | blocker | Open, escalated: no CI | a | b |
| PE-R3-01 | major | Open | a | b |

| Finding | Severity | Disposition | Files | Evidence |
|---|---|---|---|---|
| PE-R3-05 | blocker | Not fixed: needs the PO | a | b |
"""
    rows = m.open_defects(text)
    assert len(rows) == 2
    assert sorted(rows[0]["ids"] + rows[1]["ids"]) == ["PE-R3-01", "PE-R3-05", "QA-R3-05"]


def test_open_defects_a_finding_closed_in_one_alias_stays_open_in_the_other() -> None:
    # Fail closed: QA-R3-05's latest row is open even though PE-R3-05's latest row is fixed.
    text = """
| Finding | Severity | Disposition | Files | Evidence |
|---|---|---|---|---|
| PE-R3-05 / QA-R3-05 | blocker | Open, escalated: no CI | a | b |
| PE-R3-05 | blocker | Fixed: run 1 green | a | b |
"""
    assert len(m.open_defects(text)) == 1
    closed = text.replace("Open, escalated: no CI", "Fixed: duplicate of PE-R3-05")
    assert m.open_defects(closed) == []
