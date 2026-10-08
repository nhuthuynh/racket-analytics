"""PE-R1S3-07 / QA-R1S3-07 (review round 2): red-first E2E rows are listed, not gated.

The backend gate selects ``not red_until`` and lists the red-until rows in a separate step
(``red_until_report.py``, sprint-02 §8). Playwright had no equivalent, so the red-first Sprint 3
specs (E2E-03-01..06) failed ``ci-gate`` at every head until their stories land, and a real
Sprint 0-2 E2E regression was hidden in the same red job (blockers.md 2026-10-07).

Mechanism (proposed by sre-devops-engineer, ADR 0046): a QA-owned spec carries the Playwright
tag ``@red-until-<story>`` (``test(title, { tag: '@red-until-ST-047' }, …)`` or on its
``describe``). The gated E2E step runs ``--grep-invert @red-until-``; a second step runs only the
tagged specs with the JSON reporter, and ``scripts/ci/e2e_red_until_report.py`` lists them per
story and **fails closed**: a tagged test that passes (stale tag), an empty selection, a selected
test without a story tag, or an unreadable report.
"""

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


def report(tmp: Path, tests: list[tuple[str, list[str], str, str]]) -> Path:
    """tests: (title, tags as the JSON reporter writes them (no '@'), project, last result)."""
    specs = []
    for title, tags, project, result in tests:
        status = {"passed": "expected", "skipped": "skipped"}.get(result, "unexpected")
        specs.append(
            {
                "title": title,
                "tags": tags,
                "file": "sprint-03/journey-v2.spec.ts",
                "tests": [
                    {
                        "projectName": project,
                        "status": status,
                        "results": [{"status": result}],
                    }
                ],
            }
        )
    body = {
        "suites": [
            {
                "title": "sprint-03/journey-v2.spec.ts",
                "specs": specs[:1],
                "suites": [{"title": "nested describe", "specs": specs[1:], "suites": []}],
            }
        ]
        if specs
        else [],
        "errors": [],
    }
    path = tmp / "e2e-red-until.json"
    path.write_text(json.dumps(body))
    return path


def run(path: Path, summary: Path | None = None) -> subprocess.CompletedProcess:
    args = [sys.executable, str(SCRIPT), "--json", str(path)]
    if summary:
        args += ["--summary", str(summary)]
    return subprocess.run(args, capture_output=True, text=True, check=False)


def e2e_steps() -> list[dict]:
    return yaml.safe_load(CI.read_text())["jobs"]["e2e"]["steps"]


def playwright_steps() -> list[dict]:
    return [s for s in e2e_steps() if "playwright test" in s.get("run", "")]


# ---------------------------------------------------------------- negative cases first
def test_a_missing_report_fails_closed(tmp_path: Path) -> None:
    res = run(tmp_path / "none.json")
    assert res.returncode == 2, res


def test_an_unreadable_report_fails_closed(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert run(bad).returncode == 2


def test_an_empty_selection_fails_closed(tmp_path: Path) -> None:
    res = run(report(tmp_path, []))
    assert res.returncode == 1
    assert "no red-until" in res.stdout


def test_a_tagged_test_that_passes_is_a_stale_tag(tmp_path: Path) -> None:
    res = run(
        report(
            tmp_path,
            [
                ("E2E-03-01 stats", ["red-until-ST-047"], "chromium", "failed"),
                ("E2E-03-07 move offer", ["red-until-ST-048"], "webkit", "passed"),
            ],
        )
    )
    assert res.returncode == 1
    assert "stale" in res.stdout
    assert "ST-048" in res.stdout
    assert "webkit" in res.stdout


def test_a_selected_test_without_a_story_tag_fails(tmp_path: Path) -> None:
    res = run(report(tmp_path, [("E2E-03-04 delete", ["slow"], "chromium", "failed")]))
    assert res.returncode == 1
    assert "no story" in res.stdout


def test_a_tag_with_no_story_id_is_not_a_story(tmp_path: Path) -> None:
    res = run(report(tmp_path, [("E2E-03-04 delete", ["red-until-"], "chromium", "failed")]))
    assert res.returncode == 1
    assert "no story" in res.stdout


def test_a_report_with_top_level_errors_fails(tmp_path: Path) -> None:
    path = report(tmp_path, [("E2E-03-01 stats", ["red-until-ST-047"], "chromium", "failed")])
    body = json.loads(path.read_text())
    body["errors"] = [{"message": "SyntaxError: sprint-03/states.spec.ts"}]
    path.write_text(json.dumps(body))
    res = run(path)
    assert res.returncode == 1
    assert "SyntaxError" in res.stdout


def test_the_gated_e2e_step_leaves_out_the_red_until_specs() -> None:
    gated = [s for s in playwright_steps() if "--grep-invert" in s["run"]]
    assert len(gated) == 1, playwright_steps()
    assert f'--grep-invert "{TAG}"' in gated[0]["run"]
    assert "|| " not in gated[0]["run"]
    assert not gated[0].get("continue-on-error", False)


def test_the_listed_step_can_not_hide_a_stale_tag() -> None:
    names = [s.get("name", "") for s in e2e_steps()]
    listed = [s for s in playwright_steps() if f'--grep "{TAG}"' in s["run"]]
    assert len(listed) == 1, playwright_steps()
    rep = [s for s in e2e_steps() if "e2e_red_until_report.py" in s.get("run", "")]
    assert len(rep) == 1
    assert "|| " not in rep[0]["run"]
    assert not rep[0].get("continue-on-error", False)
    assert "if" not in rep[0], "the report must run whenever the listed step ran"
    # Gated first, then listed, then the report (as in the integration job).
    gated = next(s for s in playwright_steps() if "--grep-invert" in s["run"])
    order = [names.index(s.get("name", "")) for s in (gated, listed[0], rep[0])]
    assert order == sorted(order), order


# ---------------------------------------------------------------- positive
def test_failing_tagged_tests_are_listed_per_story_and_do_not_fail(tmp_path: Path) -> None:
    summary = tmp_path / "summary.md"
    res = run(
        report(
            tmp_path,
            [
                ("E2E-03-01 stats", ["red-until-ST-047"], "chromium", "failed"),
                ("E2E-03-01 stats", ["red-until-ST-047"], "webkit", "timedOut"),
                ("E2E-03-02 coach-reviewed", ["@red-until-COACH-1"], "chromium", "failed"),
                ("E2E-03-06 narrow", ["red-until-QA-R1S3-01", "a11y"], "chromium", "skipped"),
            ],
        ),
        summary,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    text = summary.read_text()
    assert "| ST-047 | 2 | 0 | 0 |" in text
    assert "| COACH-1 | 1 | 0 | 0 |" in text
    assert "| QA-R1S3-01 | 0 | 0 | 1 |" in text
    assert "not gated" in text.lower()


def test_the_listed_step_writes_the_json_report_the_script_reads() -> None:
    listed = next(s for s in playwright_steps() if f'--grep "{TAG}"' in s["run"])
    out = listed.get("env", {}).get("PLAYWRIGHT_JSON_OUTPUT_NAME", "")
    assert "--reporter=json" in listed["run"]
    assert out, listed
    rep = next(s for s in e2e_steps() if "e2e_red_until_report.py" in s.get("run", ""))
    assert Path(out).name in rep["run"]


# ---------------------------------------------------------------- ADR 0046 amendment (2026-10-08)
# The listed step counts the @red-until- tags in the spec files first (a static grep). With 0
# tags nothing is waiting on a story: exit 0 with a message. With 1 or more tags and an empty
# selection it still fails closed (a broken grep or a renamed tag). PE-R3S3-05 / QA-R3S3-03.
def specs_dir(tmp: Path, tagged: bool) -> Path:
    d = tmp / "e2e" / "sprint-03"
    d.mkdir(parents=True)
    tag = ", { tag: '@red-until-ST-047' }" if tagged else ""
    (d / "journey-v2.spec.ts").write_text(f"test('E2E-03-01 stats'{tag}, async () => {{}});\n")
    (d / "notes.md").write_text("@red-until-ST-999 in a non-spec file is not a tag\n")
    return tmp / "e2e"


def test_tagged_specs_with_an_empty_selection_still_fail_closed(tmp_path: Path) -> None:
    specs = specs_dir(tmp_path, tagged=True)
    path = report(tmp_path, [])
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", str(path), "--specs", str(specs)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 1, res.stdout + res.stderr
    assert "no red-until" in res.stdout
    assert "1 tag" in res.stdout


def test_no_tagged_spec_means_nothing_is_waiting_and_passes(tmp_path: Path) -> None:
    specs = specs_dir(tmp_path, tagged=False)
    summary = tmp_path / "summary.md"
    # Playwright writes "No tests found" into the report when --grep selects nothing.
    path = report(tmp_path, [])
    body = json.loads(path.read_text())
    body["errors"] = [{"message": "Error: No tests found"}]
    path.write_text(json.dumps(body))
    res = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--json",
            str(path),
            "--specs",
            str(specs),
            "--summary",
            str(summary),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "no red-first E2E spec is waiting on a story" in res.stdout
    assert "no red-first E2E spec is waiting on a story" in summary.read_text()


def test_the_report_step_counts_the_tags_in_the_spec_files() -> None:
    rep = next(s for s in e2e_steps() if "e2e_red_until_report.py" in s.get("run", ""))
    assert "--specs web/e2e" in rep["run"], rep["run"]
