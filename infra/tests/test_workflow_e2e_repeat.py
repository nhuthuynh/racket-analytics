"""CI-FLAKE-RESUMABLE (NFR-074): .github/workflows/e2e-repeat.yml runs scripts/ci/e2e_repeat.sh
to repeat one E2E spec in CI. Its verdicts are bound in tests/features/e2e_repeat_triage.feature."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

WF = REPO_ROOT / ".github" / "workflows" / "e2e-repeat.yml"
SCRIPT = REPO_ROOT / "scripts" / "ci" / "e2e_repeat.sh"


def workflow() -> dict:
    assert WF.is_file(), f"{WF.relative_to(REPO_ROOT)} is missing"
    return yaml.safe_load(WF.read_text())


def triggers() -> dict:
    wf = workflow()
    return wf.get("on", wf.get(True))  # PyYAML reads the bare key `on` as True


def steps() -> list[dict]:
    return workflow()["jobs"]["repeat"]["steps"]


def run_script(env: dict[str, str], tmp_path: Path) -> subprocess.CompletedProcess[str]:
    assert SCRIPT.is_file(), f"{SCRIPT.relative_to(REPO_ROOT)} is missing"
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT / "web",
        env={"PATH": "/usr/bin:/bin", "REPORT_DIR": str(tmp_path), **env},
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


# ---------------------------------------------------------------- negative cases first
def test_inputs_never_reach_a_shell_line_directly() -> None:
    # Script injection: a dispatch input is data, so it goes through env, never `${{ }}` in run.
    for step in steps():
        assert "${{ inputs." not in step.get("run", ""), step.get("name")
        assert "${{ github.event.inputs." not in step.get("run", ""), step.get("name")


def test_an_empty_dispatch_grep_reaches_the_script_unchanged() -> None:
    # PE-PR10-M1: `inputs.grep || '<default>'` turns an empty dispatch grep into the default,
    # since '' is falsy in Actions expressions. The script picks the default from EVENT instead.
    env = next(s["env"] for s in steps() if "bash ../scripts/ci/e2e_repeat.sh" in s.get("run", ""))
    assert env["GREP"] == "${{ inputs.grep }}"
    assert env["EVENT"] == "${{ github.event_name }}"


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"SPEC": "../backend/tests/x.spec.ts"}, "spec must be"),
        ({"SPEC": "e2e/../../etc/passwd.spec.ts"}, "spec must be"),
        ({"SPEC": "e2e/sprint-01/resumable-upload.spec.ts; rm -rf /"}, "spec must be"),
        ({"REPEAT": "0"}, "repeat must be"),
        ({"REPEAT": "100"}, "repeat must be"),
        ({"REPEAT": "20 --retries=3"}, "repeat must be"),
        ({"PROJECT": "firefox"}, "project must be"),
    ],
)
def test_a_bad_input_is_refused_before_playwright_runs(
    env: dict[str, str], message: str, tmp_path: Path
) -> None:
    res = run_script(env, tmp_path)
    assert res.returncode == 2, res.stdout + res.stderr
    assert message in res.stderr
    assert not (tmp_path / "e2e-repeat.xml").exists()


def test_it_never_retries() -> None:
    assert "--retries" not in SCRIPT.read_text()
    assert "retries: 0" in (REPO_ROOT / "web" / "playwright.config.ts").read_text()


def test_token_is_read_only_and_the_job_has_a_timeout() -> None:
    wf = workflow()
    assert wf["permissions"] == {"contents": "read"}
    assert 0 < wf["jobs"]["repeat"]["timeout-minutes"] <= 90


# ---------------------------------------------------------------- positive cases
def test_dispatch_takes_spec_grep_repeat_and_browser() -> None:
    inputs = triggers()["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"spec", "grep", "repeat", "project"}
    assert inputs["spec"]["default"] == "e2e/sprint-01/resumable-upload.spec.ts"
    assert inputs["repeat"]["default"] == "20"
    assert inputs["project"]["type"] == "choice"
    assert inputs["project"]["options"] == ["chromium", "webkit"]
    assert inputs["project"]["default"] == "chromium"


def test_a_pr_that_changes_the_triage_tooling_or_the_spec_runs_it() -> None:
    paths = triggers()["pull_request"]["paths"]
    for path in (
        ".github/workflows/e2e-repeat.yml",
        "scripts/ci/e2e_repeat.sh",
        "web/e2e/helpers/upload-hold.ts",
        "web/e2e/sprint-01/resumable-upload.spec.ts",
    ):
        assert path in paths


def test_it_runs_the_script_on_the_compose_stack_over_https_like_the_e2e_job() -> None:
    runs = "\n".join(s.get("run", "") for s in steps())
    assert "$COMPOSE up -d --build --wait" in runs
    assert "bash ../scripts/ci/e2e_repeat.sh" in runs
    env = {k: v for s in steps() for k, v in (s.get("env") or {}).items()}
    assert env["BASE_URL"] == "https://localhost:3000"
    for name in ("SPEC", "GREP", "REPEAT", "PROJECT"):
        assert name in env, name


def test_the_reports_are_kept_even_when_the_job_fails() -> None:
    uploads = [s for s in steps() if str(s.get("uses", "")).startswith("actions/upload-artifact@")]
    assert uploads
    assert uploads[0].get("if") == "always()"
