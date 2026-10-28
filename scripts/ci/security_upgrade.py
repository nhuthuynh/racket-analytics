#!/usr/bin/env python3
"""Security upgrade planner for the daily dependency audit (CI-DAILY-AUDIT; NFR-062; ADR 0053).

Reads pip-audit JSON reports (one per uv project) and, optionally, a `pnpm audit --json` report.
For every vulnerable Python package with a fix version it runs `uv lock --upgrade-package <pkg>`
in the affected project, then checks the lock really moved. It writes, into --out-dir:

* pr-title.txt, pr-body.md   when at least one package was upgraded;
* issue-title.txt, issue-body.md   when an advisory has no fix version, uv could not move the
  package, or web has a critical advisory (web is never upgraded automatically);
* summary.json   always: {"upgraded": n, "unfixed": n}.

It never touches git or GitHub: .github/workflows/dependency-audit.yml commits, pushes and opens
the draft pull request or the issue. Stdlib only, so it runs on a bare runner Python.
Usage: security_upgrade.py --root . --audit backend=b.json [--audit infra=i.json]
       [--web-audit w.json] --date YYYY-MM-DD [--uv uv] --out-dir reports/deps
Exit 0 done, 2 a report or project is missing or unreadable (fail closed).
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PR_TITLE = "[DEPS-AUDIT] security upgrades {date}"
ISSUE_TITLE = "[DEPS-AUDIT] advisories without an automatic fix"
PROJECT_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


class AuditError(Exception):
    """An audit report or project that cannot be read: the job fails closed."""


@dataclass(frozen=True)
class Finding:
    """One advisory against one locked Python package of one uv project."""

    project: str
    package: str
    version: str
    advisory: str
    aliases: tuple[str, ...]
    fix_versions: tuple[str, ...]

    @property
    def fixable(self) -> bool:
        return bool(self.fix_versions)


@dataclass(frozen=True)
class WebFinding:
    """One critical advisory from `pnpm audit` (reported, never upgraded automatically)."""

    package: str
    version: str
    advisory: str
    patched: str
    url: str


def normalise(name: str) -> str:
    """PEP 503 name, as uv.lock writes it."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _load(text: str, what: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AuditError(f"{what}: audit report is not JSON ({exc})") from exc


def parse_pip_audit(text: str, project: str) -> list[Finding]:
    doc = _load(text, project)
    deps = doc.get("dependencies") if isinstance(doc, dict) else None
    if not isinstance(deps, list):
        raise AuditError(f"{project}: pip-audit report has no 'dependencies' list")
    findings = []
    for d in deps:
        if "skip_reason" in d:  # not on PyPI (the project itself); pip-audit cannot judge it
            continue
        for v in d.get("vulns", []):
            findings.append(
                Finding(
                    project=project,
                    package=normalise(d["name"]),
                    version=d["version"],
                    advisory=v["id"],
                    aliases=tuple(v.get("aliases", [])),
                    fix_versions=tuple(v.get("fix_versions", [])),
                )
            )
    return findings


def parse_pnpm_audit(text: str, level: str = "critical") -> list[WebFinding]:
    doc = _load(text, "web")
    advisories = doc.get("advisories") if isinstance(doc, dict) else None
    if not isinstance(advisories, dict):
        raise AuditError("web: pnpm audit report has no 'advisories' map")
    found = []
    for a in advisories.values():
        if a.get("severity") != level:
            continue
        versions = sorted({f.get("version", "?") for f in a.get("findings", [])})
        found.append(
            WebFinding(
                package=a.get("module_name", "?"),
                version=", ".join(versions),
                advisory=a.get("github_advisory_id") or str(a.get("id", "?")),
                patched=a.get("patched_versions", "?"),
                url=a.get("url", ""),
            )
        )
    return found


def plan_upgrades(findings: Sequence[Finding]) -> dict[str, list[str]]:
    """project -> sorted packages to pass to `uv lock --upgrade-package`."""
    plan: dict[str, set[str]] = {}
    for f in findings:
        if f.fixable:
            plan.setdefault(f.project, set()).add(f.package)
    return {project: sorted(pkgs) for project, pkgs in sorted(plan.items())}


def locked_version(lock: Path, package: str) -> str | None:
    doc = tomllib.loads(lock.read_text())
    want = normalise(package)
    for p in doc.get("package", []):
        if normalise(p.get("name", "")) == want:
            return p.get("version")
    return None


def run_uv(argv: list[str], cwd: Path) -> None:
    subprocess.run(argv, cwd=cwd, check=True)


def upgrade(plan: dict[str, list[str]], root: Path, uv: list[str]) -> dict[tuple[str, str], str]:
    """Run one `uv lock --upgrade-package ...` per project; return (project, package) -> the
    newly locked version, for the packages whose locked version really moved."""
    upgraded: dict[tuple[str, str], str] = {}
    for project, packages in plan.items():
        lock = root / project / "uv.lock"
        before = {p: locked_version(lock, p) for p in packages}
        argv = [*uv, "lock"]
        for p in packages:
            argv += ["--upgrade-package", p]
        run_uv(argv, root / project)
        for p in packages:
            after = locked_version(lock, p)
            if after and after != before[p]:
                upgraded[(project, p)] = after
    return upgraded


def pr_title(date: str) -> str:
    return PR_TITLE.format(date=date)


def _ids(f: Finding) -> str:
    return ", ".join([f.advisory, *f.aliases])


def pr_body(findings: Sequence[Finding], upgraded: dict[tuple[str, str], str], date: str) -> str:
    rows = [
        f"| {f.project} | {f.package} | {_ids(f)} | {f.version} | "
        f"{', '.join(f.fix_versions)} | {upgraded[(f.project, f.package)]} |"
        for f in findings
        if (f.project, f.package) in upgraded
    ]
    return "\n".join(
        [
            f"Daily dependency audit of {date} (CI-DAILY-AUDIT, NFR-062, ADR 0053).",
            "",
            "`uv lock --upgrade-package` moved each package below to a version with the fix.",
            "",
            "| Project | Package | Advisory | Locked | Fixed in | Now locked |",
            "|---|---|---|---|---|---|",
            *rows,
            "",
            "## Review and merge",
            "",
            "- Opened by the scheduled workflow as a **draft**. A pull request pushed with",
            "  `GITHUB_TOKEN` starts no other workflow, so CI runs when a reviewer marks it",
            "  **ready for review** (ADR 0053). Every update turns it back into a draft.",
            "- Reviewers required: principal-engineer + senior-qa-engineer.",
            "- Merged only by the gated merge step after `merge_ready.py` passes; this job never",
            "  merges and never applies a policy label.",
            "",
        ]
    )


def issue_body(
    unfixed: Sequence[Finding], web: Sequence[WebFinding], stuck: Sequence[Finding]
) -> str:
    lines = [
        "The daily dependency audit (CI-DAILY-AUDIT, ADR 0053) found advisories it cannot fix",
        "with an automatic upgrade. Each needs a ticket: upgrade by hand, replace the package,",
        "or record an accepted risk in an ADR.",
        "",
        "| Ecosystem | Project | Package | Advisory | Locked | Why not upgraded |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| Python | {f.project} | {f.package} | {_ids(f)} | {f.version} | no fix version |"
        for f in unfixed
    ]
    lines += [
        f"| Python | {f.project} | {f.package} | {_ids(f)} | {f.version} | "
        f"still locked after `uv lock --upgrade-package` (fix: {', '.join(f.fix_versions)}) |"
        for f in stuck
    ]
    lines += [
        f"| npm | web | {w.package} | {w.advisory} | {w.version} | "
        f"critical; web is not upgraded automatically (patched: {w.patched}) |"
        for w in web
    ]
    return "\n".join([*lines, ""])


def _audit_arg(value: str) -> tuple[str, Path]:
    project, sep, path = value.partition("=")
    if not sep or not PROJECT_NAME.match(project):
        raise AuditError(f"--audit {value!r}: expected PROJECT=PATH with a plain directory name")
    return project, Path(path)


def _read(path: Path, what: str) -> str:
    try:
        return path.read_text()
    except OSError as exc:
        raise AuditError(f"{what}: cannot read audit report {path} ({exc})") from exc


def run(args: argparse.Namespace) -> dict[str, int]:
    root = Path(args.root)
    findings: list[Finding] = []
    for value in args.audit:
        project, path = _audit_arg(value)
        if not (root / project).is_dir():
            raise AuditError(f"{project}: no such project directory under {root}")
        findings += parse_pip_audit(_read(path, project), project)
    web = parse_pnpm_audit(_read(Path(args.web_audit), "web")) if args.web_audit else []

    upgraded = upgrade(plan_upgrades(findings), root, shlex.split(args.uv))
    fixable = [f for f in findings if f.fixable]
    stuck = [f for f in fixable if (f.project, f.package) not in upgraded]
    unfixed = [f for f in findings if not f.fixable]

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if upgraded:
        (out / "pr-title.txt").write_text(pr_title(args.date) + "\n")
        (out / "pr-body.md").write_text(pr_body(fixable, upgraded, args.date))
    if unfixed or stuck or web:
        (out / "issue-title.txt").write_text(ISSUE_TITLE + "\n")
        (out / "issue-body.md").write_text(issue_body(unfixed, web, stuck))
    summary = {"upgraded": len(upgraded), "unfixed": len(unfixed) + len(stuck) + len(web)}
    (out / "summary.json").write_text(json.dumps(summary) + "\n")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--audit", action="append", default=[], help="PROJECT=pip-audit.json")
    ap.add_argument("--web-audit", help="pnpm audit --json report")
    ap.add_argument("--date", required=True)
    ap.add_argument("--uv", default="uv", help="uv command (default: uv)")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    if not args.audit:
        print("security_upgrade: no --audit report given", file=sys.stderr)
        return 2
    try:
        summary = run(args)
    except AuditError as exc:
        print(f"security_upgrade: {exc}", file=sys.stderr)
        return 2
    print(f"security_upgrade: {summary['upgraded']} upgraded, {summary['unfixed']} need an issue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
