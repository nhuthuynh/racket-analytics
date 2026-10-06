"""Regression guards for the first CI run on main (run 37277549983, Sprint 1).

* `docker compose up --wait` fails when a named service is a one-shot that exits, even
  with code 0 ("container ...-objectstore-init-1 exited (0)"). One-shots run with
  `compose run --rm` after the long-running services are healthy.
* `FORCE_COLOR=1` makes `uv export` write ANSI colour codes into the requirements file,
  which pip-audit cannot parse. Exports pass `--color never` and write with `-o`.
* anchore/sbom-action does not create the parent of `output-file`; the job creates
  `reports/` first.
"""

from __future__ import annotations

import pytest
import yaml
from conftest import REPO_ROOT
from test_workflows_round1 import jobs

pytestmark = pytest.mark.unit

COMPOSE_FILE = REPO_ROOT / "infra" / "compose.yaml"
WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))


def one_shot_services() -> set[str]:
    services = yaml.safe_load(COMPOSE_FILE.read_text())["services"]
    return {
        name
        for name, svc in services.items()
        if svc.get("restart") == "no" and "healthcheck" not in svc
    }


def all_run_steps() -> list[tuple[str, str, str]]:
    out = []
    for wf in WORKFLOWS:
        for job_name, job in (yaml.safe_load(wf.read_text()).get("jobs") or {}).items():
            for step in job.get("steps", []):
                if "run" in step:
                    out.append((wf.name, job_name, step["run"]))
    return out


# ---------------------------------------------------------------- negative cases first
def test_compose_up_wait_never_names_a_one_shot_service() -> None:
    one_shots = one_shot_services()
    assert "objectstore-init" in one_shots
    for wf, job, run in all_run_steps():
        for line in run.splitlines():
            if "up" in line.split() and "--wait" in line:
                named = set(line.split()) & one_shots
                assert not named, f"{wf}:{job}: `up --wait` names one-shot {named}: {line}"


def test_uv_export_is_colourless_and_written_with_output_flag() -> None:
    exports = [(wf, job, run) for wf, job, run in all_run_steps() if "uv export" in run]
    assert exports, "pip-audit export step not found"
    for wf, job, run in exports:
        line = next(ln for ln in run.splitlines() if "uv export" in ln)
        assert "--color never" in line, f"{wf}:{job}: {line}"
        assert " -o " in line or "--output-file" in line, f"{wf}:{job}: {line}"


def test_sbom_job_creates_the_reports_directory_before_the_sbom_steps() -> None:
    steps = jobs()["sbom-licences"]["steps"]
    first_sbom = next(i for i, s in enumerate(steps) if "sbom-action" in s.get("uses", ""))
    assert any("mkdir -p reports" in s.get("run", "") for s in steps[:first_sbom])


@pytest.mark.parametrize("job", ["integration", "flaky-report"])
def test_backing_services_jobs_still_create_the_bucket(job: str) -> None:
    runs = "\n".join(s.get("run", "") for s in jobs()[job]["steps"])
    assert "run --rm objectstore-init" in runs
