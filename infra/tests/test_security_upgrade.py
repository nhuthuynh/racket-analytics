"""CI-DAILY-AUDIT unit tests for scripts/ci/security_upgrade.py over fake pip-audit and pnpm audit
JSON (vulnerable with a fix, without a fix, clean), and for .github/workflows/dependency-audit.yml.
One integration test runs the real `uv lock --upgrade-package` on a throwaway project."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR

SCRIPT = SCRIPTS_DIR / "ci" / "security_upgrade.py"
WF = REPO_ROOT / ".github" / "workflows" / "dependency-audit.yml"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("security_upgrade", SCRIPT)
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(mod)
    return mod


su = load() if SCRIPT.exists() else None


@pytest.fixture
def m() -> ModuleType:
    assert su is not None, f"{SCRIPT} does not exist"
    return su


def report(*deps: dict) -> str:
    return json.dumps({"dependencies": list(deps), "fixes": []})


def dep(name: str, version: str, *vulns: dict) -> dict:
    return {"name": name, "version": version, "vulns": list(vulns)}


def vuln(vid: str, fixes: list[str], aliases: list[str] | None = None) -> dict:
    return {"id": vid, "fix_versions": fixes, "aliases": aliases or [], "description": "d"}


WITH_FIX = report(dep("certifi", "2026.7.22", vuln("PYSEC-2026-4320", ["2026.10.19"])))
WITHOUT_FIX = report(dep("Some_Pkg", "1.0", vuln("PYSEC-2026-9999", [], ["GHSA-aaaa-bbbb-cccc"])))
CLEAN = report(dep("certifi", "2026.10.19"), {"name": "racket", "skip_reason": "not on PyPI"})


# ------------------------------------------------------------------ pip-audit (negative first)
@pytest.mark.unit
@pytest.mark.parametrize("text", ["", "not json", "[]", '{"fixes": []}', '{"dependencies": {}}'])
def test_a_broken_pip_audit_report_is_refused(m: ModuleType, text: str) -> None:
    with pytest.raises(m.AuditError, match="backend"):
        m.parse_pip_audit(text, "backend")


@pytest.mark.unit
def test_a_clean_report_has_no_finding_and_skipped_packages_are_ignored(m: ModuleType) -> None:
    assert m.parse_pip_audit(CLEAN, "backend") == []


@pytest.mark.unit
def test_a_vulnerable_package_with_a_fix_is_a_fixable_finding(m: ModuleType) -> None:
    (f,) = m.parse_pip_audit(WITH_FIX, "backend")
    assert (f.project, f.package, f.version, f.advisory) == (
        "backend",
        "certifi",
        "2026.7.22",
        "PYSEC-2026-4320",
    )
    assert f.fix_versions == ("2026.10.19",)
    assert f.fixable


@pytest.mark.unit
def test_a_vulnerable_package_without_a_fix_is_not_fixable_and_its_name_is_normalised(
    m: ModuleType,
) -> None:
    (f,) = m.parse_pip_audit(WITHOUT_FIX, "infra")
    assert f.package == "some-pkg"
    assert f.aliases == ("GHSA-aaaa-bbbb-cccc",)
    assert not f.fixable


# ------------------------------------------------------------------ plan
@pytest.mark.unit
def test_plan_upgrades_each_fixable_package_once_per_project(m: ModuleType) -> None:
    findings = [
        *m.parse_pip_audit(WITH_FIX, "backend"),
        *m.parse_pip_audit(WITH_FIX, "infra"),
        *m.parse_pip_audit(
            report(dep("certifi", "2026.7.22", vuln("A-1", ["1"]), vuln("A-2", ["2"]))), "backend"
        ),
        *m.parse_pip_audit(WITHOUT_FIX, "backend"),
    ]
    assert m.plan_upgrades(findings) == {"backend": ["certifi"], "infra": ["certifi"]}
    assert m.plan_upgrades(m.parse_pip_audit(CLEAN, "backend")) == {}


# ------------------------------------------------------------------ pnpm audit
PNPM = json.dumps(
    {
        "actions": [],
        "advisories": {
            "1": {
                "module_name": "next",
                "severity": "critical",
                "github_advisory_id": "GHSA-2464-fhr4-w9xw",
                "patched_versions": ">=15.5.28",
                "findings": [{"version": "15.5.27", "paths": [".>next"]}],
                "url": "https://github.com/advisories/GHSA-2464-fhr4-w9xw",
            },
            "2": {
                "module_name": "next",
                "severity": "high",
                "github_advisory_id": "GHSA-p3m5-59mp-jv5r",
                "patched_versions": ">=15.5.28",
                "findings": [{"version": "15.5.27", "paths": [".>next"]}],
                "url": "u",
            },
        },
        "metadata": {},
    }
)


@pytest.mark.unit
@pytest.mark.parametrize("text", ["", "nope", '{"actions": []}'])
def test_a_broken_pnpm_audit_report_is_refused(m: ModuleType, text: str) -> None:
    with pytest.raises(m.AuditError, match="web"):
        m.parse_pnpm_audit(text)


@pytest.mark.unit
def test_pnpm_audit_keeps_critical_advisories_only(m: ModuleType) -> None:
    (w,) = m.parse_pnpm_audit(PNPM)
    assert (w.package, w.version, w.advisory, w.patched) == (
        "next",
        "15.5.27",
        "GHSA-2464-fhr4-w9xw",
        ">=15.5.28",
    )
    assert m.parse_pnpm_audit(json.dumps({"advisories": {}, "metadata": {}})) == []


# ------------------------------------------------------------------ lock files
LOCK = """version = 1
revision = 3

[[package]]
name = "certifi"
version = "2026.10.19"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "some-pkg"
version = "1.0"
"""


@pytest.mark.unit
def test_locked_version_reads_the_uv_lock(m: ModuleType, tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text(LOCK)
    assert m.locked_version(tmp_path / "uv.lock", "certifi") == "2026.10.19"
    assert m.locked_version(tmp_path / "uv.lock", "Some_Pkg") == "1.0"
    assert m.locked_version(tmp_path / "uv.lock", "absent") is None


# ------------------------------------------------------------------ texts
@pytest.mark.unit
def test_pr_title_names_the_date(m: ModuleType) -> None:
    assert m.pr_title("2026-10-28") == "[DEPS-AUDIT] security upgrades 2026-10-28"


@pytest.mark.unit
def test_pr_body_lists_advisory_versions_and_the_review_gates(m: ModuleType) -> None:
    findings = m.parse_pip_audit(WITH_FIX, "backend")
    body = m.pr_body(findings, {("backend", "certifi"): "2026.10.19"}, "2026-10-28")
    row = next(line for line in body.splitlines() if "PYSEC-2026-4320" in line)
    for cell in ("backend", "certifi", "2026.7.22", "2026.10.19"):
        assert cell in row
    assert "principal-engineer" in body
    assert "senior-qa-engineer" in body
    assert "ready for review" in body.lower()


@pytest.mark.unit
def test_issue_body_lists_unfixed_python_and_critical_web_advisories(m: ModuleType) -> None:
    body = m.issue_body(m.parse_pip_audit(WITHOUT_FIX, "backend"), m.parse_pnpm_audit(PNPM), [])
    assert any("PYSEC-2026-9999" in r and "some-pkg" in r for r in body.splitlines())
    assert any("GHSA-2464-fhr4-w9xw" in r and ">=15.5.28" in r for r in body.splitlines())
    assert "GHSA-p3m5-59mp-jv5r" not in body


# ------------------------------------------------------------------ main
def write(tmp: Path, name: str, text: str) -> Path:
    p = tmp / name
    p.write_text(text)
    return p


@pytest.mark.unit
def test_main_fails_closed_on_a_missing_report(m: ModuleType, tmp_path: Path) -> None:
    rc = m.main(
        [
            "--root",
            str(tmp_path),
            "--audit",
            f"backend={tmp_path / 'nope.json'}",
            "--date",
            "2026-10-28",
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )
    assert rc == 2


@pytest.mark.unit
def test_main_refuses_an_unknown_project_directory(m: ModuleType, tmp_path: Path) -> None:
    rc = m.main(
        [
            "--root",
            str(tmp_path),
            "--audit",
            f"../etc={write(tmp_path, 'a.json', CLEAN)}",
            "--date",
            "2026-10-28",
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )
    assert rc == 2


@pytest.mark.unit
def test_main_reports_a_package_uv_could_not_move_in_the_issue(
    m: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    (root / "backend").mkdir(parents=True)
    (root / "backend" / "uv.lock").write_text(LOCK.replace("2026.10.19", "2026.7.22"))
    calls: list[tuple[list[str], Path]] = []
    # uv leaves the lock unchanged, as when a constraint holds the package back
    monkeypatch.setattr(m, "run_uv", lambda argv, cwd: calls.append((argv, cwd)))
    rc = m.main(
        [
            "--root",
            str(root),
            "--audit",
            f"backend={write(tmp_path, 'b.json', WITH_FIX)}",
            "--date",
            "2026-10-28",
            "--uv",
            "uv",
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )
    assert rc == 0
    assert calls == [(["uv", "lock", "--upgrade-package", "certifi"], root / "backend")]
    assert not (tmp_path / "out" / "pr-body.md").exists()
    issue = (tmp_path / "out" / "issue-body.md").read_text()
    assert any("PYSEC-2026-4320" in r and "still" in r.lower() for r in issue.splitlines())
    summary = json.loads((tmp_path / "out" / "summary.json").read_text())
    assert summary == {"upgraded": 0, "unfixed": 1}


@pytest.mark.unit
def test_main_with_a_clean_audit_writes_only_the_summary(m: ModuleType, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "backend").mkdir(parents=True)
    rc = m.main(
        [
            "--root",
            str(root),
            "--audit",
            f"backend={write(tmp_path, 'c.json', CLEAN)}",
            "--web-audit",
            write(tmp_path, "w.json", '{"advisories": {}, "metadata": {}}').as_posix(),
            "--date",
            "2026-10-28",
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )
    assert rc == 0
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["summary.json"]


# ------------------------------------------------------------------ workflow
def wf() -> dict:
    return yaml.safe_load(WF.read_text())


@pytest.mark.unit
def test_workflow_exists_with_one_timed_job_on_a_pinned_runner() -> None:
    (job,) = wf()["jobs"].values()
    assert job["runs-on"] == "ubuntu-24.04"
    assert 0 < job["timeout-minutes"] <= 30


@pytest.mark.unit
def test_workflow_runs_one_audit_at_a_time_and_never_cancels_a_push() -> None:
    assert wf()["concurrency"] == {"group": "dependency-audit", "cancel-in-progress": False}


@pytest.mark.unit
def test_workflow_never_force_pushes_the_upgrade_branch() -> None:
    text = "\n".join(s.get("run", "") for s in next(iter(wf()["jobs"].values()))["steps"])
    pushes = [line for line in text.splitlines() if "git push" in line]
    assert pushes
    for line in pushes:
        for flag in ("--force", " -f", "+refs", " +"):
            assert flag not in line, line


@pytest.mark.unit
def test_workflow_runs_the_tested_script() -> None:
    assert "scripts/ci/security_upgrade.py" in WF.read_text()


# ------------------------------------------------------------------ real uv
@pytest.mark.integration
@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not installed")
def test_real_uv_lock_upgrades_the_named_package(m: ModuleType, tmp_path: Path) -> None:
    proj = tmp_path / "backend"
    proj.mkdir()
    py = proj / "pyproject.toml"
    py.write_text(
        '[project]\nname = "p"\nversion = "0"\nrequires-python = ">=3.11"\n'
        'dependencies = ["idna==3.6"]\n[tool.uv]\npackage = false\n'
    )
    subprocess.run(["uv", "lock", "--quiet"], cwd=proj, check=True, timeout=120)
    py.write_text(py.read_text().replace("idna==3.6", "idna>=3.6"))
    subprocess.run(["uv", "lock", "--quiet"], cwd=proj, check=True, timeout=120)
    assert m.locked_version(proj / "uv.lock", "idna") == "3.6"
    audit = write(tmp_path, "a.json", report(dep("idna", "3.6", vuln("PYSEC-2024-60", ["3.7"]))))
    rc = m.main(
        [
            "--root",
            str(tmp_path),
            "--audit",
            f"backend={audit}",
            "--date",
            "2026-10-28",
            "--uv",
            "uv",
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )
    assert rc == 0
    new = m.locked_version(proj / "uv.lock", "idna")
    assert new
    assert new != "3.6"
    assert new in (tmp_path / "out" / "pr-body.md").read_text()
