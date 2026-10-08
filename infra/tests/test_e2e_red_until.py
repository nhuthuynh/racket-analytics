"""PE-R1S3-07 / QA-R1S3-07: red-first E2E specs tagged ``@red-until-<story>`` are listed, not
gated, and ``scripts/ci/e2e_red_until_report.py`` fails closed (ADR 0046 and its amendment;
PR #12 review round 1: M1, QA-PR12-01 for the 0-tag cases)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

SCRIPT = REPO_ROOT / "scripts" / "ci" / "e2e_red_until_report.py"
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
TAG = "@red-until-"
Row = tuple[str, list[str], str, str]  # title, tags (no "@" in JSON), project, result


def report(tmp: Path, tests: list[Row], errors: tuple[str, ...] = ()) -> Path:
    specs = [
        {
            "title": title,
            "tags": tags,
            "file": "sprint-03/journey-v2.spec.ts",
            "tests": [{"projectName": project, "results": [{"status": result}]}],
        }
        for title, tags, project, result in tests
    ]
    nested = {"title": "nested describe", "specs": specs[1:], "suites": []}
    suites = [{"title": "journey-v2", "specs": specs[:1], "suites": [nested]}] if specs else []
    path = tmp / "e2e-red-until.json"
    path.write_text(json.dumps({"suites": suites, "errors": [{"message": e} for e in errors]}))
    return path


def run(path: Path, *extra: str) -> subprocess.CompletedProcess:
    args = [sys.executable, str(SCRIPT), "--json", str(path), *extra]
    return subprocess.run(args, capture_output=True, text=True, check=False)


def specs_dir(tmp: Path, tagged: bool) -> str:
    d = tmp / "e2e" / "sprint-03"
    d.mkdir(parents=True)
    tag = ", { tag: '@red-until-ST-047' }" if tagged else ""
    (d / "journey-v2.spec.ts").write_text(f"test('E2E-03-01 stats'{tag}, async () => {{}});\n")
    (d / "notes.md").write_text("@red-until-ST-999 in a non-source file is not a tag\n")
    return str(tmp / "e2e")


def e2e_steps() -> list[dict]:
    return yaml.safe_load(CI.read_text())["jobs"]["e2e"]["steps"]


def step(needle: str) -> list[dict]:
    return [s for s in e2e_steps() if needle in s.get("run", "")]


FAILING = ("E2E-03-01 stats", ["red-until-ST-047"], "chromium", "failed")
NO_TESTS = "Error: No tests found"
PASSING = ("stale one", ["red-until-ST-048"], "webkit", "passed")
SYNTAX = "SyntaxError: sprint-03/states.spec.ts"


# ---------------------------------------------------------------- negative cases first
@pytest.mark.parametrize("body", [None, "{not json"])
def test_a_missing_or_unreadable_report_fails_closed(tmp_path: Path, body: str | None) -> None:
    path = tmp_path / "r.json"
    if body:
        path.write_text(body)
    assert run(path).returncode == 2
    assert run(path, "--specs", specs_dir(tmp_path, tagged=False)).returncode == 2


FAILS_CLOSED = {  # id: (selected tests, report errors, --specs tree, expected text); all rc 1
    "empty-selection": ([], (), None, "no red-until E2E tests were selected (fail closed)"),
    "stale-tag": ([FAILING, PASSING], (), None, "stale tag, the test passes: ST-048 [webkit]"),
    "no-story": ([(*FAILING[:1], ["slow"], *FAILING[2:])], (), None, "no story in the tags"),
    "bare-tag": ([(*FAILING[:1], ["red-until-"], *FAILING[2:])], (), None, "no story in the"),
    "report-error": ([FAILING], (SYNTAX,), None, f"report error: {SYNTAX}"),
    "tagged-specs-empty": ([], (NO_TESTS,), "tagged", "although the source files carry 1 tag"),
    # PR #12 round 1 (M1, QA-PR12-01): 0 literal tags must not skip the report.
    "0-tags-but-stale": ([PASSING], (), "untagged", "stale tag, the test passes: ST-048"),
    "tag-in-a-helper": ([], (NO_TESTS,), "helper", "no red-until E2E tests were selected"),
    "0-tags-other-error": ([], (SYNTAX,), "untagged", f"report error: {SYNTAX}"),
}


@pytest.mark.parametrize("case", FAILS_CLOSED, ids=FAILS_CLOSED)
def test_the_report_fails_closed(tmp_path: Path, case: str) -> None:
    rows, errors, tree, expected = FAILS_CLOSED[case]
    extra: list[str] = []
    if tree:
        extra = ["--specs", specs_dir(tmp_path, tagged=tree == "tagged")]
    if tree == "helper":
        (Path(extra[1]) / "helpers").mkdir()
        (Path(extra[1]) / "helpers" / "tags.ts").write_text("export const W = '@red-until-X-1';")
    res = run(report(tmp_path, rows, errors), *extra)
    assert res.returncode == 1, res.stdout + res.stderr
    assert expected in res.stdout


def test_the_gated_e2e_step_leaves_out_the_red_until_specs() -> None:
    gated = step("--grep-invert")
    assert len(gated) == 1
    assert f'--grep-invert "{TAG}"' in gated[0]["run"]
    assert "|| " not in gated[0]["run"]
    assert not gated[0].get("continue-on-error", False)


def test_the_listed_step_can_not_hide_a_stale_tag() -> None:
    listed, rep = step(f'--grep "{TAG}"'), step("e2e_red_until_report.py")
    assert len(listed) == 1
    assert len(rep) == 1
    assert "|| " not in rep[0]["run"]
    assert not rep[0].get("continue-on-error", False)
    assert "if" not in rep[0], "the report must run whenever the listed step ran"
    order = [e2e_steps().index(s) for s in (step("--grep-invert")[0], listed[0], rep[0])]
    assert order == sorted(order), order  # gated, then listed, then the report


# ---------------------------------------------------------------- positive
def test_failing_tagged_tests_are_listed_per_story_and_do_not_fail(tmp_path: Path) -> None:
    summary = tmp_path / "summary.md"
    rows = [
        FAILING,
        ("E2E-03-01 stats", ["red-until-ST-047"], "webkit", "timedOut"),
        ("E2E-03-02 coach-reviewed", ["@red-until-COACH-1"], "chromium", "failed"),
        ("E2E-03-06 narrow", ["red-until-QA-R1S3-01", "a11y"], "chromium", "skipped"),
        ("E2E-03-01 stats", ["red-until-ST-047b"], "chromium", "failed"),
    ]
    res = run(report(tmp_path, rows), "--summary", str(summary))
    assert res.returncode == 0, res.stdout + res.stderr
    text = summary.read_text()
    assert "| ST-047 | 2 | 0 | 0 |" in text
    assert "| COACH-1 | 1 | 0 | 0 |" in text
    assert "| QA-R1S3-01 | 0 | 0 | 1 |" in text
    assert "| ST-047b | 1 | 0 | 0 |" in text
    assert "not gated" in text.lower()


def test_no_tag_and_no_selection_means_nothing_is_waiting_and_passes(tmp_path: Path) -> None:
    summary = tmp_path / "summary.md"
    path = report(tmp_path, [], (NO_TESTS,))  # what Playwright writes when --grep selects nothing
    res = run(path, "--specs", specs_dir(tmp_path, tagged=False), "--summary", str(summary))
    assert res.returncode == 0, res.stdout + res.stderr
    assert "no red-first E2E spec is waiting on a story" in res.stdout
    assert "no red-first E2E spec is waiting on a story" in summary.read_text()


def test_the_listed_step_writes_the_json_report_the_script_reads() -> None:
    listed, rep = step(f'--grep "{TAG}"')[0], step("e2e_red_until_report.py")[0]
    out = listed.get("env", {}).get("PLAYWRIGHT_JSON_OUTPUT_NAME", "")
    assert "--reporter=json" in listed["run"]
    assert out, listed
    assert Path(out).name in rep["run"]
    assert "--specs web/e2e" in rep["run"], rep["run"]
