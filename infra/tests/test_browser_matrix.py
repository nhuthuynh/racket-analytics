"""ST-079 (NFR-024.1-.3; G05-04): the browser-matrix method and its nightly wiring.

``scripts/measure/browser_matrix.py`` reads the Playwright JSON reports of the ``@critical``
specs, one per project, and passes a project only when every critical journey ran, every test ran
``--repeats`` times and every run passed (retries are off, so a mixed outcome is flaky).
The scenario level is ``test_browser_matrix_scenarios.py`` (real Playwright runs).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR

pytestmark = pytest.mark.unit

sys.path.insert(0, str(SCRIPTS_DIR / "measure"))
import browser_matrix as bm  # noqa: E402

MATRIX = SCRIPTS_DIR / "measure" / "browser_matrix.py"
NIGHTLY = REPO_ROOT / ".github" / "workflows" / "nightly-quality.yml"

CRITICAL = [
    ("sprint-04/journey-v3.spec.ts", "E2E-04-01 Upload to plan"),
    ("sprint-04/plan-states.spec.ts", "E2E-04-02 empty"),
    ("sprint-04/offline-done.spec.ts", "E2E-04-03 a session marked done offline"),
    ("sprint-04/swap-no-alternative.spec.ts", "E2E-04-04 a drill with no other that fits"),
    ("sprint-04/keyboard-and-narrow.spec.ts", "E2E-04-05 keyboard-only"),
    ("sprint-01/sign-in.spec.ts", "Sign up with an email sign-in link"),
    ("sprint-01/resumable-upload.spec.ts", "Connection drops mid-upload (E2E-01-02)"),
]


def report(project: str, statuses: dict[str, list[str]] | None = None, *, repeats: int = 3,
           specs: list[tuple[str, str]] | None = None) -> dict:
    """A Playwright JSON report: one spec per (file, title), one test entry per repeat."""
    statuses = statuses or {}
    suites = []
    for file, title in specs if specs is not None else CRITICAL:
        runs = statuses.get(title, ["expected"] * repeats)
        tests = [{"projectName": project, "status": s, "results": [{"status": "passed"}]} for s in runs]
        suites.append({"file": file, "specs": [{"file": file, "title": title, "tests": tests}],
                       "suites": []})
    return {"config": {}, "suites": suites, "stats": {}}


def test_journey_of_names_each_critical_journey() -> None:
    assert [bm.journey_of(f, t) for f, t in CRITICAL] == [
        "E2E-04-01", "E2E-04-02", "E2E-04-03", "E2E-04-04", "E2E-04-05", "sign-in", "upload-resume",
    ]
    assert bm.journey_of("sprint-01/resumable-upload.spec.ts", "Upload page wording") is None
    assert bm.journey_of("sprint-04/journey-v3.spec.ts", "E2E-04-011 x") is None


def test_a_project_where_every_journey_passes_three_times_is_ok() -> None:
    result = bm.judge(bm.collect([report("android-chrome")]), ["android-chrome"], repeats=3)
    assert result["ok"] is True
    p = result["projects"]["android-chrome"]
    assert (p["ok"], p["passed"], p["failed"], p["flaky"], p["missing"]) == (True, 7, [], [], [])


@pytest.mark.parametrize(
    ("runs", "bucket"),
    [
        (["expected", "unexpected", "expected"], "flaky"),
        (["expected", "flaky", "expected"], "flaky"),
        (["unexpected", "unexpected", "unexpected"], "failed"),
    ],
)
def test_a_mixed_or_failing_journey_fails_its_project(runs: list[str], bucket: str) -> None:
    rep = report("webkit", {"E2E-04-03 a session marked done offline": runs})
    p = bm.judge(bm.collect([rep]), ["webkit"], repeats=3)["projects"]["webkit"]
    assert p["ok"] is False
    assert p[bucket] == ["E2E-04-03 a session marked done offline"]


def test_a_test_with_fewer_runs_than_repeats_fails() -> None:
    rep = report("chromium", {"E2E-04-01 Upload to plan": ["expected", "expected"]})
    p = bm.judge(bm.collect([rep]), ["chromium"], repeats=3)["projects"]["chromium"]
    assert p["ok"] is False
    assert p["short"] == ["E2E-04-01 Upload to plan (2 of 3 runs)"]


def test_a_journey_that_only_skipped_counts_as_missing() -> None:
    rep = report("chromium", {"Sign up with an email sign-in link": ["skipped"] * 3})
    p = bm.judge(bm.collect([rep]), ["chromium"], repeats=3)["projects"]["chromium"]
    assert p["ok"] is False
    assert p["missing"] == ["sign-in"]
    assert p["skipped"] == ["Sign up with an email sign-in link"]


def test_a_skipped_test_beside_a_passing_one_does_not_fail_the_journey() -> None:
    extra = [*CRITICAL, ("sprint-01/sign-in.spec.ts", "A link that can no longer be used: is 16 minutes old")]
    rep = report("chromium", {extra[-1][1]: ["skipped"] * 3}, specs=extra)
    p = bm.judge(bm.collect([rep]), ["chromium"], repeats=3)["projects"]["chromium"]
    assert p["ok"] is True
    assert p["skipped"] == [extra[-1][1]]


def test_a_required_project_absent_from_every_report_fails_closed() -> None:
    result = bm.judge(bm.collect([report("chromium")]), ["chromium", "firefox"], repeats=3)
    assert result["ok"] is False
    assert result["projects"]["firefox"] == {"ok": False, "no_report": True}
    assert result["projects"]["chromium"]["ok"] is True


def test_a_report_with_two_projects_is_split_by_project() -> None:
    rep = report("chromium")
    rep["suites"] += report("webkit", {"E2E-04-05 keyboard-only": ["unexpected"] * 3})["suites"]
    result = bm.judge(bm.collect([rep]), ["chromium", "webkit"], repeats=3)
    assert result["projects"]["chromium"]["ok"] is True
    assert result["projects"]["webkit"]["failed"] == ["E2E-04-05 keyboard-only"]


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(MATRIX), *args], capture_output=True, text=True,
                          timeout=60, check=False)


def test_cli_prints_one_line_per_project_and_writes_json(tmp_path: Path) -> None:
    files = []
    for project in ("chromium", "android-chrome"):
        files.append(tmp_path / f"pw-{project}.json")
        files[-1].write_text(json.dumps(report(project)))
    out = tmp_path / "matrix.json"
    proc = run(*map(str, files), "--require", "chromium,android-chrome", "--json", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "chromium: ok (7 passed x 3)" in proc.stdout
    assert "android-chrome: ok (7 passed x 3)" in proc.stdout
    assert json.loads(out.read_text())["ok"] is True


def test_cli_planted_failure_require_firefox_is_rc_1(tmp_path: Path) -> None:
    f = tmp_path / "pw-chromium.json"
    f.write_text(json.dumps(report("chromium")))
    proc = run(str(f), "--require", "chromium,firefox")
    assert proc.returncode == 1
    assert "firefox: no report" in proc.stdout


def test_cli_malformed_report_or_no_require_is_rc_2(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert run(str(bad), "--require", "chromium").returncode == 2
    good = tmp_path / "good.json"
    good.write_text(json.dumps(report("chromium")))
    assert run(str(good), "--require", "").returncode == 2


# ---------------------------------------------------------------- nightly wiring (G05-04)
def test_the_nightly_browser_matrix_job_runs_the_g05_04_command_for_three_projects() -> None:
    job = yaml.safe_load(NIGHTLY.read_text())["jobs"]["browser-matrix"]
    script = "\n".join(str(s.get("run", "")) for s in job["steps"])
    assert "for p in chromium webkit android-chrome" in script
    assert "PW_PROJECTS=$p" in script
    assert "--repeat-each 3 --grep @critical" in script
    assert "--reporter json" in script
    assert "scripts/measure/browser_matrix.py reports/pw-*.json --require chromium,webkit,android-chrome" in script
    # Google Chrome (runner image) for chromium and android-chrome; never a browser named after a project
    assert "playwright install --with-deps chromium webkit" in script


def test_the_browser_matrix_does_not_block_the_nightly_publish() -> None:
    wf = yaml.safe_load(NIGHTLY.read_text())
    assert "browser-matrix" not in wf["jobs"]["publish"].get("needs", [])
