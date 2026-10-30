"""SRE-VERIFY04R3-03: the coaching gates of sprint-04 §8 are wired (retro C5, finding M7).

* ``nightly-quality.yml`` mutates ``coaching/plan`` and ``coaching/weakness`` with a 0.80
  minimum, each from a fresh ``mutants/``, and publishes both scores to the sprint status file.
* ``ci.yml``'s ``DOMAIN_TEST_PATHS`` holds ``tests/unit/coaching`` inside the unchanged 10 s
  budget; the ci-profile property step therefore runs the coaching property tests too.
* No test under ``DOMAIN_TEST_PATHS`` pins the ci profile's example count itself, so the
  domain step keeps measuring the default profile (ADR 0049; QA-R1-07).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from coaching_gates import (
    COACHING_TARGETS,
    COACHING_TESTS,
    MIN_SCORE,
    coaching_step,
    mutation_job,
    option,
    publish_run,
    publish_scopes,
    score_argv,
)
from conftest import SCRIPTS_DIR
from domain_budget import BACKEND, ci_env, expand, positionals, unit_steps

pytestmark = pytest.mark.unit

CI = SCRIPTS_DIR / "ci"
STATS = {"killed": 79, "survived": 21, "total": 100, "no_tests": 0, "skipped": 0, "timeout": 0}


def run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CI / script), *args], capture_output=True,
                          text=True, timeout=60, check=False)  # fmt: skip


def status_file(tmp_path: Path) -> Path:
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"sprint": "04"}))
    return path


# ---------------------------------------------------------------- negative cases first
def test_a_coaching_score_below_the_minimum_fails_and_the_report_says_so(tmp_path: Path) -> None:
    stats = tmp_path / "stats.json"
    stats.write_text(json.dumps(STATS))
    out = tmp_path / "m.json"
    res = run("mutation_score.py", "--from-stats", str(stats), "--target",
              "src/racket/coaching/plan", "--min-score", "0.80", "--out", str(out))  # fmt: skip
    assert res.returncode == 1, res.stdout
    report = json.loads(out.read_text())
    assert (report["score"], report["min_score"], report["gate"]) == (0.79, 0.8, "failed")


def test_a_run_with_no_score_fails_its_minimum_never_passes(tmp_path: Path) -> None:
    stats = tmp_path / "stats.json"
    stats.write_text(json.dumps({**STATS, "killed": 0, "survived": 0, "total": 0}))
    out = tmp_path / "m.json"
    res = run("mutation_score.py", "--from-stats", str(stats), "--target", "src/x",
              "--min-score", "0.80", "--out", str(out))  # fmt: skip
    assert res.returncode == 1
    assert json.loads(out.read_text())["gate"] == "failed"


def test_a_missing_coaching_report_is_recorded_as_no_report_never_passed(tmp_path: Path) -> None:
    status = status_file(tmp_path)
    res = run("nightly_status.py", "--status", str(status), "--run-url", "u", "--sha", "abc",
              "--mutation-job", "failure",
              "--mutation-scope", f"coaching/plan={tmp_path / 'none.json'}")  # fmt: skip
    assert res.returncode == 0, res.stderr
    entry = json.loads(status.read_text())["nightly"]["mutation_scopes"]["coaching/plan"]
    assert entry["status"] == "no_report"
    assert entry["score"] is None
    assert entry.get("gate") != "passed"
    assert entry["job"] == "failure"


def test_a_mutation_scope_without_a_path_is_refused(tmp_path: Path) -> None:
    res = run("nightly_status.py", "--status", str(status_file(tmp_path)), "--run-url", "u",
              "--sha", "abc", "--mutation-scope", "coaching/plan")  # fmt: skip
    assert res.returncode == 2
    assert "SCOPE=PATH" in res.stderr


def test_no_domain_test_pins_the_ci_profile_example_count() -> None:
    # A test with its own max_examples >= the ci profile's 1,000 runs ci-profile work inside the
    # 10 s domain budget, which measures the default profile (ADR 0049; QA-R1-07). Such tests take
    # their count from the profile; the ci-profile property step gives them >= 1,000.
    pinned = []
    for rel in ci_env()["DOMAIN_TEST_PATHS"].split():
        for path in sorted((BACKEND / rel).rglob("test_*.py")):
            for m in re.finditer(r"max_examples\s*=\s*([\d_]+)", path.read_text()):
                if int(m.group(1).replace("_", "")) >= 1000:
                    pinned.append(f"{path.relative_to(BACKEND)}: {m.group(0)}")
    assert pinned == []


def test_the_rules_mutation_run_is_unchanged() -> None:
    argv = score_argv("src/racket/sports/pickleball/rules")
    assert option(argv, "--tests") == "tests/unit/sports"
    assert option(argv, "--ignore") == "tests/unit/sports/pickleball/test_rules_static.py"
    assert option(argv, "--out") == "../reports/mutation.json"


# ---------------------------------------------------------------- positive cases
def test_ci_domain_test_paths_include_the_coaching_unit_tests() -> None:
    paths = ci_env()["DOMAIN_TEST_PATHS"].split()
    assert COACHING_TESTS in paths
    assert (BACKEND / COACHING_TESTS).is_dir()
    assert ci_env()["DOMAIN_UNIT_BUDGET_S"] == "10"


def test_the_ci_profile_property_step_runs_the_coaching_tests() -> None:
    prop = [s for s in unit_steps() if s.get("env", {}).get("HYPOTHESIS_PROFILE") == "ci"]
    assert len(prop) == 1
    line = next(ln for ln in prop[0]["run"].splitlines() if "run_with_budget.py" in ln)
    argv = expand(line.strip(), ci_env())
    assert COACHING_TESTS in positionals(argv[argv.index("pytest") + 1 :])
    conftest = (BACKEND / "tests" / "conftest.py").read_text()
    assert re.search(r'"ci",\s*max_examples=1000', conftest)


@pytest.mark.parametrize("scope", sorted(COACHING_TARGETS))
def test_the_nightly_job_scores_each_coaching_target_against_080(scope: str) -> None:
    target = COACHING_TARGETS[scope]
    argv = score_argv(target)
    assert option(argv, "--project") == "."
    assert option(argv, "--tests") == COACHING_TESTS
    assert option(argv, "--min-score") == MIN_SCORE
    assert option(argv, "--out") == f"../reports/mutation-{scope.replace('/', '-')}.json"
    step = coaching_step(target)
    # mutmut 3 keeps earlier results in ./mutants; each target starts from an empty one.
    run_ = step["run"]
    assert run_.index("rm -rf mutants") < run_.index("mutation_score.py")
    # A red rules run (or the other target) must not skip this target.
    assert step["if"] == "success() || failure()"
    assert "mutmut==${MUTMUT_VERSION}" in run_


def test_each_coaching_report_reaches_the_status_file() -> None:
    job = mutation_job()
    for scope in COACHING_TARGETS:
        key = scope.replace("/", "_")
        assert job["outputs"][key] == f"${{{{ steps.report.outputs.{key} }}}}"
    assert publish_scopes() == {
        scope: f"reports/mutation-{scope.replace('/', '-')}.json" for scope in COACHING_TARGETS
    }
    run_ = publish_run()
    for scope in COACHING_TARGETS:
        env = scope.replace("/", "_").upper()
        assert f'"${env}_REPORT"' in run_


def test_the_coaching_reports_are_kept_as_artifacts() -> None:
    upload = next(s for s in mutation_job()["steps"] if "upload-artifact" in s.get("uses", ""))
    assert "reports/mutation*.json" in upload["with"]["path"]
