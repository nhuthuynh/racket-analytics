"""ST-002: helper scripts behind the CI gates (sprint-00 §3.1, §8)."""

from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit

CI = SCRIPTS_DIR / "ci"


def run(
    script: str,
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float = 60,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CI / script), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout,
        check=False,
        env={**os.environ, **(env or {})},
    )


# ================================================================ run_with_budget (NFR-073)
def test_budget_exceeded_fails_even_if_command_would_pass() -> None:
    res = run("run_with_budget.py", "1", "--", "sleep", "3", timeout=10)
    assert res.returncode == 124
    assert "exceeded its time budget of 1" in res.stdout


def test_budget_command_failure_is_propagated() -> None:
    res = run("run_with_budget.py", "10", "--", "sh", "-c", "exit 3")
    assert res.returncode == 3


def test_budget_within_limit_passes_and_reports_time() -> None:
    res = run("run_with_budget.py", "10", "--", "true")
    assert res.returncode == 0
    assert "within budget" in res.stdout


# ================================================================ check_licences (NFR-062)
def sbom(tmp: Path, components: list[dict]) -> Path:
    p = tmp / "sbom.json"
    p.write_text(
        json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.5", "components": components})
    )
    return p


def comp(
    name: str, *, lic_id: str | None = None, lic_name: str | None = None, expr: str | None = None
) -> dict:
    lic: list[dict] = []
    if lic_id:
        lic.append({"license": {"id": lic_id}})
    if lic_name:
        lic.append({"license": {"name": lic_name}})
    if expr:
        lic.append({"expression": expr})
    return {"type": "library", "name": name, "version": "1.0", "licenses": lic}


@pytest.mark.parametrize(
    "component",
    [
        comp("ultra", lic_id="AGPL-3.0-only"),
        comp("ultra2", lic_name="GNU Affero General Public License v3"),
        comp("nc", lic_id="CC-BY-NC-4.0"),
        comp("nc2", lic_name="Free for non-commercial use"),
        comp("poly", lic_id="PolyForm-Noncommercial-1.0.0"),
        comp("either", expr="MIT AND AGPL-3.0-or-later"),
        comp("sspl", lic_id="SSPL-1.0"),
        comp("busl", lic_id="BUSL-1.1"),
    ],
)
def test_denied_licence_fails_and_names_the_package(tmp_path: Path, component: dict) -> None:
    res = run(
        "check_licences.py", "--sbom", str(sbom(tmp_path, [comp("ok", lic_id="MIT"), component]))
    )
    assert res.returncode == 1
    assert component["name"] in res.stdout


def test_allowlisted_exception_passes_with_reason(tmp_path: Path) -> None:
    allow = tmp_path / "allow.json"
    allow.write_text(json.dumps({"exceptions": [{"name": "ultra", "reason": "ADR 9999 test"}]}))
    res = run(
        "check_licences.py",
        "--sbom",
        str(sbom(tmp_path, [comp("ultra", lic_id="AGPL-3.0-only")])),
        "--allow",
        str(allow),
    )
    assert res.returncode == 0
    assert "ADR 9999" in res.stdout


def test_allowlist_entry_without_reason_is_rejected(tmp_path: Path) -> None:
    allow = tmp_path / "allow.json"
    allow.write_text(json.dumps({"exceptions": [{"name": "ultra"}]}))
    res = run(
        "check_licences.py",
        "--sbom",
        str(sbom(tmp_path, [comp("ultra", lic_id="AGPL-3.0-only")])),
        "--allow",
        str(allow),
    )
    assert res.returncode == 2


def test_permissive_and_lgpl_pass_and_unknown_is_listed(tmp_path: Path) -> None:
    components = [
        comp("a", lic_id="MIT"),
        comp("b", lic_id="Apache-2.0"),
        comp("psycopg", lic_id="LGPL-3.0-only"),
        comp("mystery"),
    ]
    res = run("check_licences.py", "--sbom", str(sbom(tmp_path, components)))
    assert res.returncode == 0, res.stdout
    assert "mystery" in res.stdout
    assert "unknown" in res.stdout.lower()


def test_unreadable_sbom_fails_closed(tmp_path: Path) -> None:
    bad = tmp_path / "x.json"
    bad.write_text("{")
    assert run("check_licences.py", "--sbom", str(bad)).returncode == 2


def test_empty_sbom_fails_closed(tmp_path: Path) -> None:
    res = run("check_licences.py", "--sbom", str(sbom(tmp_path, [])))
    assert res.returncode == 2
    assert "no components" in res.stdout


# ================================================================ flaky_report (NFR-074)
def junit(tmp: Path, name: str, results: dict[str, str]) -> Path:
    cases = []
    for test, outcome in results.items():
        cls, case = test.rsplit("::", 1)
        body = {
            "pass": "",
            "fail": "<failure message='boom'/>",
            "skip": "<skipped/>",
            "error": "<error message='e'/>",
        }[outcome]
        cases.append(f'<testcase classname="{cls}" name="{case}" time="0.01">{body}</testcase>')
    p = tmp / name
    p.write_text(
        f'<?xml version="1.0"?><testsuites><testsuite name="pytest">{"".join(cases)}'
        "</testsuite></testsuites>"
    )
    return p


def test_mixed_outcomes_across_runs_are_reported_as_flaky(tmp_path: Path) -> None:
    r1 = junit(
        tmp_path, "r1.xml", {"t.a::test_1": "pass", "t.a::test_2": "pass", "t.a::test_3": "fail"}
    )
    r2 = junit(
        tmp_path, "r2.xml", {"t.a::test_1": "fail", "t.a::test_2": "pass", "t.a::test_3": "fail"}
    )
    out = tmp_path / "report.md"
    res = run("flaky_report.py", "--out", str(out), str(r1), str(r2))
    assert res.returncode == 0
    text = out.read_text()
    assert "t.a::test_1" in text
    assert "t.a::test_2" not in text
    assert "t.a::test_3" not in text  # consistently failing is broken, not flaky
    assert "1 flaky" in text


def test_fail_on_flaky_flag_turns_the_report_into_a_gate(tmp_path: Path) -> None:
    r1 = junit(tmp_path, "r1.xml", {"t::x": "pass"})
    r2 = junit(tmp_path, "r2.xml", {"t::x": "error"})
    res = run(
        "flaky_report.py", "--fail-on-flaky", "--out", str(tmp_path / "o.md"), str(r1), str(r2)
    )
    assert res.returncode == 1


def test_stable_runs_report_zero_flaky(tmp_path: Path) -> None:
    r1 = junit(tmp_path, "r1.xml", {"t::x": "pass", "t::y": "skip"})
    r2 = junit(tmp_path, "r2.xml", {"t::x": "pass", "t::y": "skip"})
    out = tmp_path / "o.md"
    assert (
        run("flaky_report.py", "--fail-on-flaky", "--out", str(out), str(r1), str(r2)).returncode
        == 0
    )
    assert "0 flaky" in out.read_text()


# ================================================================ check_pr_size (EP/ENG-04)
def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
        },
    )


@pytest.fixture
def size_repo(tmp_path: Path) -> Path:
    r = tmp_path / "r"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    (r / "README.md").write_text("x\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "base")
    git(r, "checkout", "-q", "-b", "pr")
    return r


def add_lines(repo: Path, rel: str, n: int) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(f"line {i}\n" for i in range(n)))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "c")


def test_pr_over_400_lines_fails_without_waiver(size_repo: Path) -> None:
    add_lines(size_repo, "backend/src/big.py", 401)
    res = run("check_pr_size.py", "--base", "main", cwd=size_repo, env={"PR_LABELS": "[]"})
    assert res.returncode == 1
    assert "401" in res.stdout


def test_pr_over_400_lines_passes_with_em_waiver(size_repo: Path) -> None:
    add_lines(size_repo, "backend/src/big.py", 401)
    res = run(
        "check_pr_size.py", "--base", "main", cwd=size_repo, env={"PR_LABELS": '["size-waiver"]'}
    )
    assert res.returncode == 0


def test_lockfiles_and_fixtures_do_not_count(size_repo: Path) -> None:
    add_lines(size_repo, "backend/uv.lock", 900)
    add_lines(size_repo, "web/pnpm-lock.yaml", 900)
    add_lines(size_repo, "fixtures/clips/synthetic-60s/manifest.json", 900)
    add_lines(size_repo, "backend/src/small.py", 50)
    res = run("check_pr_size.py", "--base", "main", cwd=size_repo, env={"PR_LABELS": "[]"})
    assert res.returncode == 0, res.stdout
    assert "50 changed lines" in res.stdout


def test_between_100_and_400_lines_warns_but_passes(size_repo: Path) -> None:
    add_lines(size_repo, "backend/src/mid.py", 150)
    res = run("check_pr_size.py", "--base", "main", cwd=size_repo, env={"PR_LABELS": "[]"})
    assert res.returncode == 0
    assert "::warning" in res.stdout


# ================================================================ check_first_route_js (NFR-015)
def next_build(tmp: Path, page_bytes: int) -> Path:
    nxt = tmp / ".next"
    (nxt / "static" / "chunks").mkdir(parents=True)
    # random-ish content so gzip cannot shrink it away
    (nxt / "static" / "chunks" / "main.js").write_bytes(os.urandom(20_000))
    (nxt / "static" / "chunks" / "page.js").write_bytes(os.urandom(page_bytes))
    (nxt / "static" / "chunks" / "polyfills.js").write_bytes(os.urandom(500_000))
    (nxt / "static" / "chunks" / "other.js").write_bytes(os.urandom(500_000))
    (nxt / "build-manifest.json").write_text(
        json.dumps(
            {
                "rootMainFiles": ["static/chunks/main.js"],
                "polyfillFiles": ["static/chunks/polyfills.js"],
                "pages": {"/_app": []},
            }
        )
    )
    (nxt / "app-build-manifest.json").write_text(
        json.dumps(
            {
                "pages": {
                    "/page": ["static/chunks/main.js", "static/chunks/page.js"],
                    "/other/page": ["static/chunks/other.js"],
                },
            }
        )
    )
    return nxt


def test_first_route_over_budget_fails(tmp_path: Path) -> None:
    nxt = next_build(tmp_path, 250_000)
    res = run("check_first_route_js.py", "--next-dir", str(nxt), "--budget-kb", "200")
    assert res.returncode == 1
    assert "over budget" in res.stdout


def test_first_route_within_budget_passes_and_ignores_polyfills(tmp_path: Path) -> None:
    nxt = next_build(tmp_path, 50_000)
    res = run("check_first_route_js.py", "--next-dir", str(nxt), "--budget-kb", "200")
    assert res.returncode == 0, res.stdout
    expected = sum(
        len(gzip.compress((nxt / "static/chunks" / f).read_bytes())) for f in ("main.js", "page.js")
    )
    assert f"{expected / 1024:.1f} KB" in res.stdout


def test_missing_build_output_fails_closed(tmp_path: Path) -> None:
    res = run("check_first_route_js.py", "--next-dir", str(tmp_path / "nope"), "--budget-kb", "200")
    assert res.returncode == 2
