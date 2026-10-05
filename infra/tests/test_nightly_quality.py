"""ST-024: nightly quality jobs (NFR-002b differential oracle, NFR-072 mutation baseline) and
their results in the sprint status file (sprint-01 §3.1, §14.3.8).

Scripts: ``scripts/ci/mutation_score.py`` and ``scripts/ci/nightly_status.py``.
Workflow: ``.github/workflows/nightly-quality.yml``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR

pytestmark = pytest.mark.unit

CI = SCRIPTS_DIR / "ci"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "nightly-quality.yml"
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def run(script: str, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CI / script), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=60,
        check=False,
        env={**os.environ, "PATH": os.environ.get("PATH", "")},
    )


def write(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def status(tmp_path: Path) -> Path:
    return write(tmp_path / "status.json", {"sprint": "01", "stories": [{"id": "ST-024"}]})


ORACLE_PASS = {
    "sequences": 100000,
    "disagreements": 0,
    "passed": True,
    "seed": 20261005,
    "seconds": 12.5,
    "shortest": None,
    "configs": [],
}
ORACLE_FAIL = {
    **ORACLE_PASS,
    "disagreements": 3,
    "passed": False,
    "shortest": {"sequence": [["won", "A"]], "expected": [1, 0], "actual": [0, 0]},
}
STATS = {
    "killed": 80,
    "survived": 15,
    "total": 100,
    "no_tests": 0,
    "skipped": 0,
    "suspicious": 0,
    "timeout": 5,
    "check_was_interrupted_by_user": 0,
    "segfault": 0,
}


# ================================================================ mutation_score.py
def test_missing_mutation_target_fails_closed(tmp_path: Path) -> None:
    out = tmp_path / "m.json"
    res = run(
        "mutation_score.py",
        "--project",
        str(tmp_path),
        "--target",
        "src/nope",
        "--tests",
        "tests",
        "--out",
        str(out),
    )
    assert res.returncode == 1
    report = json.loads(out.read_text())
    assert report["status"] == "target_missing"
    assert report["score"] is None


def test_mutation_score_from_stats_counts_timeouts_as_detected(tmp_path: Path) -> None:
    out = tmp_path / "m.json"
    stats = write(tmp_path / "stats.json", STATS)
    res = run(
        "mutation_score.py", "--from-stats", str(stats), "--target", "src/x", "--out", str(out)
    )
    assert res.returncode == 0, res.stderr
    report = json.loads(out.read_text())
    assert report["status"] == "measured"
    assert report["score"] == 0.85
    assert (report["killed"], report["survived"], report["total"]) == (80, 15, 100)


def test_mutation_report_names_its_scope_as_the_contract_does(tmp_path: Path) -> None:
    out = tmp_path / "m.json"
    stats = write(tmp_path / "stats.json", STATS)
    run(
        "mutation_score.py",
        "--from-stats",
        str(stats),
        "--target",
        "src/racket/sports/pickleball/rules",
        "--out",
        str(out),
    )
    assert json.loads(out.read_text())["scope"] == "sports/pickleball/rules"


def test_mutation_score_with_no_mutants_is_unknown(tmp_path: Path) -> None:
    out = tmp_path / "m.json"
    stats = write(
        tmp_path / "stats.json", {**STATS, "killed": 0, "survived": 0, "timeout": 0, "total": 0}
    )
    res = run(
        "mutation_score.py", "--from-stats", str(stats), "--target", "src/x", "--out", str(out)
    )
    assert res.returncode == 1
    assert json.loads(out.read_text())["status"] == "no_mutants"


def test_mutants_that_were_never_tested_give_no_score(tmp_path: Path) -> None:
    out = tmp_path / "m.json"
    untested = {**STATS, "killed": 0, "survived": 0, "timeout": 0, "total": 239}
    stats = write(tmp_path / "stats.json", untested)
    res = run(
        "mutation_score.py", "--from-stats", str(stats), "--target", "src/x", "--out", str(out)
    )
    assert res.returncode == 1
    report = json.loads(out.read_text())
    assert report["status"] == "not_checked"
    assert report["score"] is None


def test_mutation_run_refuses_to_overwrite_an_existing_setup_cfg(tmp_path: Path) -> None:
    (tmp_path / "src" / "x").mkdir(parents=True)
    (tmp_path / "setup.cfg").write_text("[metadata]\n")
    res = run(
        "mutation_score.py",
        "--project",
        str(tmp_path),
        "--target",
        "src/x",
        "--tests",
        "tests",
        "--out",
        str(tmp_path / "m.json"),
    )
    assert res.returncode == 2
    assert "setup.cfg" in res.stderr
    assert (tmp_path / "setup.cfg").read_text() == "[metadata]\n"


def _fake_mutmut(tmp_path: Path) -> dict[str, str]:
    """A ``mutmut`` on PATH that saves the setup.cfg it was started with, then does nothing."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "mutmut"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import pathlib, shutil, sys\n"
        "if sys.argv[1:] == ['run']:\n"
        f"    shutil.copy('setup.cfg', {str(tmp_path / 'seen.cfg')!r})\n"
    )
    fake.chmod(0o755)
    return {**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}"}


def test_mutation_run_keeps_source_scanning_tests_out_of_the_mutant_test_set(
    tmp_path: Path,
) -> None:
    """PE-R1-S1-01: mutmut 3 adds a ``mutmut`` import to every mutated file, so a static
    import scan (IT-01-13) fails on the instrumented copy and mutmut stops before scoring.
    The run must be able to leave such tests out; they still run in the normal suite."""
    (tmp_path / "src" / "x").mkdir(parents=True)
    static = "tests/unit/sports/pickleball/test_rules_static.py"
    res = subprocess.run(
        [
            sys.executable,
            str(CI / "mutation_score.py"),
            "--project",
            str(tmp_path),
            "--target",
            "src/x",
            "--tests",
            "tests/unit/sports",
            "--ignore",
            static,
            "--out",
            str(tmp_path / "m.json"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=_fake_mutmut(tmp_path),
    )
    assert res.returncode == 1, res.stderr  # the fake writes no stats: never a pass
    seen = (tmp_path / "seen.cfg").read_text()
    assert f"pytest_add_cli_args =\n    --ignore={static}\n" in seen
    assert "pytest_add_cli_args_test_selection =\n    tests/unit/sports/\n" in seen
    assert not (tmp_path / "setup.cfg").exists()


def test_mutation_run_without_ignore_adds_no_pytest_args(tmp_path: Path) -> None:
    (tmp_path / "src" / "x").mkdir(parents=True)
    res = subprocess.run(
        [
            sys.executable,
            str(CI / "mutation_score.py"),
            "--project",
            str(tmp_path),
            "--target",
            "src/x",
            "--out",
            str(tmp_path / "m.json"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=_fake_mutmut(tmp_path),
    )
    assert res.returncode == 1, res.stderr
    assert "pytest_add_cli_args =" not in (tmp_path / "seen.cfg").read_text()


def test_mutation_run_never_scores_a_stale_stats_file_from_an_earlier_run(
    tmp_path: Path,
) -> None:
    """QA-V1-03: when mutmut stops early it writes no new stats; a stats file left in
    ``mutants/`` by an earlier run must not be scored as this run's result."""
    (tmp_path / "src" / "x").mkdir(parents=True)
    (tmp_path / "mutants").mkdir()
    (tmp_path / "mutants" / "mutmut-cicd-stats.json").write_text(
        json.dumps({"killed": 10, "survived": 0, "total": 10, "no_tests": 0, "timeout": 0})
    )
    out = tmp_path / "m.json"
    res = subprocess.run(
        [
            sys.executable,
            str(CI / "mutation_score.py"),
            "--project",
            str(tmp_path),
            "--target",
            "src/x",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=_fake_mutmut(tmp_path),
    )
    assert res.returncode == 1, res.stdout
    report = json.loads(out.read_text())
    assert report["score"] is None
    assert report["status"] == "no_stats"


# ================================================================ nightly_status.py
def test_a_missing_oracle_report_is_recorded_as_not_run_never_passed(
    status: Path, tmp_path: Path
) -> None:
    res = run(
        "nightly_status.py",
        "--status",
        str(status),
        "--oracle",
        str(tmp_path / "none"),
        "--oracle-job",
        "failure",
        "--date",
        "2026-10-06",
        "--run-url",
        "u",
        "--sha",
        "abc",
    )
    assert res.returncode == 0, res.stderr
    nightly = json.loads(status.read_text())["nightly"]
    assert nightly["oracle"]["status"] == "no_report"
    assert nightly["oracle"]["job"] == "failure"
    assert nightly["oracle"].get("passed") is not True
    assert nightly["mutation"]["status"] == "no_report"


def test_an_oracle_disagreement_is_recorded_with_the_shortest_sequence(
    status: Path, tmp_path: Path
) -> None:
    oracle = write(tmp_path / "o.json", ORACLE_FAIL)
    run(
        "nightly_status.py",
        "--status",
        str(status),
        "--oracle",
        str(oracle),
        "--date",
        "2026-10-06",
        "--run-url",
        "u",
        "--sha",
        "abc",
    )
    o = json.loads(status.read_text())["nightly"]["oracle"]
    assert o["status"] == "failed"
    assert o["disagreements"] == 3
    assert o["shortest"]["sequence"] == [["won", "A"]]


def test_nightly_results_show_oracle_result_mutation_score_and_run_date(
    status: Path, tmp_path: Path
) -> None:
    oracle = write(tmp_path / "o.json", ORACLE_PASS)
    mutation = write(
        tmp_path / "m.json",
        {
            "status": "measured",
            "score": 0.85,
            "killed": 80,
            "survived": 15,
            "total": 100,
            "target": "src/x",
        },
    )
    res = run(
        "nightly_status.py",
        "--status",
        str(status),
        "--oracle",
        str(oracle),
        "--mutation",
        str(mutation),
        "--date",
        "2026-10-06",
        "--run-url",
        "https://github.com/o/r/actions/runs/1",
        "--sha",
        "abc123",
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(status.read_text())
    assert data["stories"] == [{"id": "ST-024"}]  # the rest of the file is untouched
    n = data["nightly"]
    assert n["run_date"] == "2026-10-06"
    assert n["run_url"] == "https://github.com/o/r/actions/runs/1"
    assert n["commit"] == "abc123"
    assert n["oracle"]["status"] == "passed"
    assert n["oracle"]["sequences"] == 100000
    assert n["mutation"]["score"] == 0.85
    assert status.read_text().endswith("\n")


def test_auto_picks_the_highest_numbered_sprint_status_file(tmp_path: Path) -> None:
    for sprint in ("00", "01", "02"):
        (tmp_path / "docs" / "sprints" / sprint).mkdir(parents=True)
    for sprint in ("00", "01"):
        write(tmp_path / "docs" / "sprints" / sprint / "status.json", {"sprint": sprint})
    res = run(
        "nightly_status.py",
        "--status",
        "auto",
        "--date",
        "2026-10-06",
        "--run-url",
        "u",
        "--sha",
        "abc",
        cwd=tmp_path,
    )
    assert res.returncode == 0, res.stderr
    assert "nightly" in json.loads(
        (tmp_path / "docs" / "sprints" / "01" / "status.json").read_text()
    )
    assert "nightly" not in json.loads(
        (tmp_path / "docs" / "sprints" / "00" / "status.json").read_text()
    )


# ================================================================ workflow
def wf() -> dict:
    return yaml.safe_load(WORKFLOW.read_text())


def test_nightly_workflow_runs_on_a_schedule_and_by_hand() -> None:
    on = wf()[True]  # PyYAML reads the bare `on:` key as boolean True
    assert on["schedule"][0]["cron"]
    assert "workflow_dispatch" in on
    assert "pull_request" not in on
    assert "push" not in on


def test_only_the_publish_job_can_write_and_only_on_the_default_branch() -> None:
    w = wf()
    assert w["permissions"] == {"contents": "read"}
    for name, job in w["jobs"].items():
        perms = job.get("permissions", {})
        if name == "publish":
            assert perms == {"contents": "write"}
            assert "default_branch" in job["if"]
            assert "always()" in job["if"]
        else:
            assert perms.get("contents", "read") == "read", name


def test_oracle_job_runs_100000_sequences_and_mutation_job_targets_the_rules() -> None:
    jobs = wf()["jobs"]
    oracle_runs = "\n".join(s.get("run", "") for s in jobs["oracle"]["steps"])
    assert "tests.oracle.differential --sequences 100000" in oracle_runs
    mutation_runs = "\n".join(s.get("run", "") for s in jobs["mutation"]["steps"])
    assert "mutation_score.py" in mutation_runs
    assert "src/racket/sports/pickleball/rules" in mutation_runs
    assert "mutmut==" in mutation_runs  # pinned


def test_mutation_job_leaves_the_static_rules_scan_out_of_the_mutant_test_set() -> None:
    """PE-R1-S1-01: with IT-01-13 in the set, mutmut 3.8 stops at 'failed to collect stats'."""
    mutation_runs = "\n".join(s.get("run", "") for s in wf()["jobs"]["mutation"]["steps"])
    assert "--ignore tests/unit/sports/pickleball/test_rules_static.py" in mutation_runs
    assert "--tests tests/unit/sports" in mutation_runs


def test_publish_writes_the_sprint_status_file_and_skips_ci() -> None:
    publish = wf()["jobs"]["publish"]
    assert set(publish["needs"]) == {"oracle", "mutation"}
    runs = "\n".join(s.get("run", "") for s in publish["steps"])
    assert "nightly_status.py --status auto" in runs
    assert "[skip ci]" in runs


def test_actions_are_pinned_to_the_same_shas_as_ci() -> None:
    ci_pins = {
        s["uses"]
        for job in yaml.safe_load(CI_YML.read_text())["jobs"].values()
        for s in job.get("steps", [])
        if "uses" in s
    }
    for job in wf()["jobs"].values():
        for step in job["steps"]:
            if "uses" in step:
                assert step["uses"] in ci_pins, step["uses"]
