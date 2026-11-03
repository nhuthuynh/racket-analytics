#!/usr/bin/env python3
"""Merge readiness check (CI-PR-GATE; PO rule 2026-10-07; docs/ops/branch-protection.md).

A pull request may merge into `main` only when, on its current head SHA:
  * every current CI check run concluded success (a non-gate run may be `skipped` or `neutral`, e.g.
    the schedule-only flaky report), and the tier's gate check itself concluded success;
  * the verdict set of the PR's review tier (CI-TIERS-b, ADR 0056) starts with "Verdict: APPROVE"
    on that SHA. The tier is computed from the changed files (`review_tiers.py`), never read:
      T0  one APPROVE from any role but the author's; gate check `doc-check`;
      T1  principal-engineer + senior-qa-engineer; gate check `ci-gate`;
      T2  T1 + security-privacy-engineer + every flagged specialist; gate check `ci-gate`;
  * an APPROVE from the PR's author role never counts. The author role is the `owner` of the head
    branch's row in docs/sprints/<nn>/ticket-owners.json on main (`<nn>` from `s<nn>/<id>`), or
    a `BOOTSTRAP_OWNERS` entry of `review_tiers.py`; never the PR body, labels or comments. A bad
    branch, a missing, duplicate or ambiguous row, or an owner that is not a role fails closed;
  * no role's latest review on that SHA says "Verdict: CHANGES REQUESTED".
All agents post as one GitHub account, so a review names its role on the line right after the
verdict ("Reviewer: <role>"). Only submitted reviews (COMMENTED, APPROVED, CHANGES_REQUESTED)
by a trusted author (author_association OWNER, MEMBER or COLLABORATOR) count, because anyone
can review a PR on a public repo and the token owner's own PENDING review is listed too.
A workflow triggered again on the same SHA (a label, a re-open) gets a new check suite; only
the current workflow run per (workflow, event) counts, so the runs another trigger left
behind (cancelled by `cancel-in-progress`, or failed) neither block nor hide a failure. The
current run is the newest run, skipping a cancelled run that a non-cancelled run created in the
same second or later replaced (a concurrency group may cancel the newer of two runs started
together, PR #49). A cancelled run nothing replaced stays current and blocks (PE-1), and a
newer failed or in-progress run always wins.

Usage: merge_ready.py --repo OWNER/NAME --pr N --sha HEAD_SHA
Env: GITHUB_TOKEN or GH_TOKEN (optional for a public repo); GITHUB_API_URL (default GitHub).
Exit codes: 0 merge-ready, 1 not ready (reasons printed), 2 GitHub could not be read.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_tiers import (
    AGENT_FILES,
    BOOTSTRAP_OWNERS,
    ChangedFile,
    Classification,
    classify,
    file_tier,
    front_matter_changed,
    glob_match,
)

GATE = "ci-gate"
DOC_CHECK = "Doc checks (paths, citations, agent front matter, decider cells)"
QA = "senior-qa-engineer"
SECURITY = "security-privacy-engineer"
# The 12 role files under .claude/agents/ (test_the_twelve_roles_are_the_role_files).
ROLES = frozenset(
    {
        "business-analyst",
        "engineering-manager",
        "pickleball-domain-coach",
        "principal-designer",
        "principal-engineer",
        "product-manager",
        "security-privacy-engineer",
        "senior-backend-engineer",
        "senior-frontend-engineer",
        "senior-ml-cv-engineer",
        "senior-qa-engineer",
        "sre-devops-engineer",
    }
)
OWNERS = "docs/sprints/{nn}/ticket-owners.json"
_TICKET_BRANCH = re.compile(r"s(\d{2})/[a-z0-9][a-z0-9._-]*")
PRINCIPAL = "principal-engineer"
SENIOR_PREFIX = "senior-"
APPROVE = "APPROVE"
CHANGES = "CHANGES REQUESTED"
CANCELLED = "cancelled"
GREEN = {"success"}
GREEN_IF_NOT_GATE = {"success", "skipped", "neutral"}
SUBMITTED = {"COMMENTED", "APPROVED", "CHANGES_REQUESTED"}
TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}
_VERDICT = re.compile(
    r"\AVerdict:\s*(APPROVE|CHANGES REQUESTED)\b[^\n]*\r?\nReviewer:\s*([a-z-]+)[ \t]*\r?$",
    re.MULTILINE,
)
_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')


# ------------------------------------------------------------------ rule (no I/O)
def _is_cancelled(wr: dict[str, Any]) -> bool:
    return wr.get("conclusion") == CANCELLED


def _replaced(cancelled: dict[str, Any], others: Sequence[dict[str, Any]]) -> bool:
    """A cancelled run is replaced when a non-cancelled run of its workflow and event was
    created in the same second or later (a concurrency group may cancel the newer of two runs
    started together, PR #49). Without both timestamps it is not replaced: missing data makes
    the check stricter, never laxer."""
    at = cancelled.get("created_at")
    return bool(at) and any(
        not _is_cancelled(o) and bool(o.get("created_at")) and o["created_at"] >= at for o in others
    )


def current_runs(workflow_runs: Sequence[dict[str, Any]]) -> dict[tuple[Any, Any], dict[str, Any]]:
    """The current workflow run per (workflow, event) on this SHA: the newest (highest id) run
    that is not a replaced cancelled run. A cancelled run nothing replaced stays current and
    blocks, because pr-policy reads the labels from that run's event payload (PE-1); a newer
    failed, queued or in-progress run always wins, so no failure is hidden."""
    groups: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
    for wr in workflow_runs:
        groups.setdefault((wr.get("workflow_id"), wr.get("event")), []).append(wr)
    return {
        key: max(
            (wr for wr in runs if not (_is_cancelled(wr) and _replaced(wr, runs))),
            key=lambda wr: wr["id"],
        )
        for key, runs in groups.items()
    }


def superseded_suites(workflow_runs: Sequence[dict[str, Any]]) -> set[Any]:
    """Check suites of workflow runs that are not the current run of their workflow and event
    on this SHA. Suites without a workflow run (other apps) are never superseded."""
    current = {wr.get("check_suite_id") for wr in current_runs(workflow_runs).values()}
    return {wr.get("check_suite_id") for wr in workflow_runs} - current


def cancelled_reasons(workflow_runs: Sequence[dict[str, Any]], sha: str) -> list[str]:
    """One reason per workflow and event whose current run on this SHA was cancelled."""
    every = {
        key
        for key in {(wr.get("workflow_id"), wr.get("event")) for wr in workflow_runs}
        if all(
            _is_cancelled(wr)
            for wr in workflow_runs
            if (wr.get("workflow_id"), wr.get("event")) == key
        )
    }
    reasons = []
    for key, wr in current_runs(workflow_runs).items():
        if not _is_cancelled(wr):
            continue
        name = wr.get("name") or wr.get("workflow_id")
        event = "" if wr.get("event") == "pull_request" else f" ({wr.get('event')})"
        if key in every:
            reasons.append(f"all {name} runs on {sha} were cancelled{event}")
        else:
            reasons.append(
                f"the newest {name} run on {sha} was cancelled and no later run replaced it{event}"
            )
    return sorted(reasons)


def latest_runs(
    check_runs: list[dict[str, Any]], workflow_runs: Sequence[dict[str, Any]] = ()
) -> dict[tuple[Any, str], dict[str, Any]]:
    """The newest run per (check suite, name) in the current suites; job re-runs get higher
    ids. Same-named jobs of two workflows are different suites, so one cannot hide the
    other's failure."""
    stale = superseded_suites(workflow_runs)
    latest: dict[tuple[Any, str], dict[str, Any]] = {}
    for run in check_runs:
        if (run.get("check_suite") or {}).get("id") in stale:
            continue
        key = ((run.get("check_suite") or {}).get("id"), run["name"])
        if key not in latest or run["id"] > latest[key]["id"]:
            latest[key] = run
    return latest


def verdicts(reviews: list[dict[str, Any]]) -> dict[str, tuple[str, str]]:
    """role -> (verdict, commit SHA) of that role's latest verdict review."""
    found: dict[str, tuple[tuple[str, int], str, str]] = {}
    for rv in reviews:
        match = _VERDICT.match((rv.get("body") or "").lstrip())
        if not match or rv.get("state") not in SUBMITTED:
            continue
        if rv.get("author_association") not in TRUSTED:
            continue
        verdict, role = match.groups()
        key = (rv.get("submitted_at") or "", rv["id"])
        if role not in found or key > found[role][0]:
            found[role] = (key, verdict, rv.get("commit_id") or "")
    return {role: (v, sha) for role, (_, v, sha) in found.items()}


def head_reasons(pr: dict[str, Any], sha: str) -> list[str]:
    """`sha` must be the head of an open PR into main (no stale-SHA merge)."""
    reasons: list[str] = []
    if pr.get("state") != "open":
        reasons.append(f"PR is {pr.get('state')}, not open")
    if pr.get("base", {}).get("ref") != "main":
        reasons.append(f"PR targets {pr.get('base', {}).get('ref')}, not main")
    if pr.get("head", {}).get("sha") != sha:
        reasons.append(f"{sha} is not the PR head ({pr.get('head', {}).get('sha')})")
    return reasons


def check_reasons(
    check_runs: list[dict[str, Any]],
    sha: str,
    workflow_runs: Sequence[dict[str, Any]] = (),
    gate: str = GATE,
) -> list[str]:
    """Every latest check run of the current suites is green; the gate check (ci-gate, or
    doc-check on tier 0) exists and succeeded."""
    current = latest_runs(check_runs, workflow_runs).values()
    runs = sorted(current, key=lambda r: (r["name"], r["id"]))
    reasons = cancelled_reasons(workflow_runs, sha)
    if not any(r["name"] == gate for r in runs):
        reasons.append(f"no {gate} check run on {sha}")
    for run in runs:
        name = run["name"]
        outcome = run.get("conclusion") if run.get("status") == "completed" else run.get("status")
        if outcome not in (GREEN if name == gate else GREEN_IF_NOT_GATE):
            reasons.append(f"check '{name}' is {outcome}")
    return reasons


class Gate(NamedTuple):
    """What a PR needs: its computed tier, author role, flagged specialists, and the problems
    that kept the author role from being computed (each one blocks the merge). A NamedTuple, not
    a dataclass: tests load this file without registering it in sys.modules."""

    tier: int = 1
    author: str | None = None
    specialists: frozenset[str] = frozenset()
    problems: tuple[str, ...] = ()

    def required(self) -> list[str]:
        """The roles whose APPROVE on the head is required (tier 1 and 2)."""
        extra = [SECURITY, *sorted(self.specialists - {PRINCIPAL, QA, SECURITY})]
        return [PRINCIPAL, QA, *(extra if self.tier >= 2 else [])]


def review_reasons(reviews: list[dict[str, Any]], sha: str, gate: Gate | None = None) -> list[str]:
    """The tier's verdict set approves the head; the author role's APPROVE never counts; nobody's
    latest verdict on the head blocks."""
    gate = gate or Gate()
    latest = verdicts(reviews)
    reasons = [
        f"{role}: Verdict: {CHANGES} on the head"
        for role, (verdict, at) in sorted(latest.items())
        if verdict == CHANGES and at == sha
    ]
    author = f" ({gate.author} authored this PR, so its own APPROVE is ignored)"
    if gate.tier == 0:
        if not any(v == (APPROVE, sha) for r, v in latest.items() if r != gate.author):
            who = author if gate.author else ""
            reasons.append(f"tier 0: no 'Verdict: {APPROVE}' on the head from another role{who}")
        return reasons
    for role in gate.required():
        found = latest.get(role)
        if role == gate.author:
            reasons.append(f"{role}: required for tier {gate.tier}, but{author}")
        elif found != (APPROVE, sha):
            label = "senior reviewer" if role == QA else role  # CI-PR-GATE message prefix kept
            reasons.append(
                f"{label}: no latest 'Verdict: {APPROVE}' on the head from {role} ({found})"
                if label != role
                else f"{role}: no latest 'Verdict: {APPROVE}' on the head ({found})"
            )
    return reasons


def review_tier(files: Iterable[ChangedFile]) -> Classification:
    """The PR's review tier and flagged specialists, computed from its changed files by the
    rules-as-data classifier (`review_tiers.py`, CI-TIERS-a); never read from a label."""
    return classify(files)


def _owner_rows(nn: str, data: bytes, branch: str) -> tuple[list[dict[str, Any]], list[str]]:
    """The rows of the Sprint `nn` owner file whose branch is `branch` or `branch`'s id followed
    by "-<slug>" (lane branches carry a slug), or the problems with the file."""
    path = OWNERS.format(nn=nn)
    try:
        doc = json.loads(data)
        tickets = doc["tickets"]
        if not isinstance(tickets, list) or not all(isinstance(t, dict) for t in tickets):
            raise TypeError("tickets is not a list of rows")
    except (ValueError, KeyError, TypeError) as exc:
        return [], [f"{path} on main is malformed ({exc}): fail closed"]
    rows = [
        t
        for t in tickets
        if isinstance(t.get("branch"), str)
        and (branch == t["branch"] or branch.startswith(t["branch"] + "-"))
    ]
    return rows, []


def resolve_author(
    branch: str, tier: int, load: Callable[[str], bytes | None]
) -> tuple[str | None, list[str]]:
    """(author role, problems) of a PR from its head branch; `load(nn)` returns the Sprint `nn`
    owner file on main, or None when main has none. Bootstrap shapes are read first."""
    for pattern, owner, max_tier in BOOTSTRAP_OWNERS:
        m = re.fullmatch(pattern, branch)
        if not m:
            continue
        if max_tier is not None and tier > max_tier:
            return None, [
                f"head branch {branch!r} may carry tier {max_tier} files only, this PR is tier "
                f"{tier}: open an s<nn>/<id> ticket"
            ]
        nn = m.groupdict().get("nn")
        data = load(nn) if nn else None
        rows, problems = _owner_rows(nn, data, branch) if nn and data is not None else ([], [])
        clash = sorted({str(r.get("owner")) for r in rows} - {owner})
        if problems or clash:
            return None, problems or [
                f"head branch {branch!r}: bootstrap owner {owner} conflicts with "
                f"{OWNERS.format(nn=nn)} row(s) naming {', '.join(clash)}: fail closed"
            ]
        return owner, []
    m = _TICKET_BRANCH.fullmatch(branch)
    if not m:
        return None, [f"head branch {branch!r} is not s<nn>/<id>: the author role is unknown"]
    nn = m.group(1)
    path = OWNERS.format(nn=nn)
    data = load(nn)
    if data is None:
        return None, [f"no {path} on main: merge s{nn}/plan first (bootstrap step)"]
    rows, problems = _owner_rows(nn, data, branch)
    if problems:
        return None, problems
    if not rows:
        return None, [
            f"no row for head branch {branch!r} in {path} on main: merge an "
            f"s{nn}/owners-<slug> PR that adds it first"
        ]
    if len(rows) > 1:
        named = ", ".join(sorted(f"{r.get('id')} ({r.get('branch')})" for r in rows))
        return None, [f"{len(rows)} rows in {path} match head branch {branch!r}: {named}"]
    row = rows[0]
    if row.get("owner") not in ROLES:
        return None, [
            f"row {row.get('id')} ({row.get('branch')}) in {path}: owner {row.get('owner')!r} "
            "is not a role file under .claude/agents/"
        ]
    return str(row["owner"]), []


def gate_for(
    pr: dict[str, Any], tiers: Classification, load: Callable[[str], bytes | None]
) -> Gate:
    """The Gate of a PR: its computed tier and specialists, and its author role from the head
    branch. Only `head.ref` of the PR is read, never its body, labels or comments."""
    author, problems = resolve_author(
        str((pr.get("head") or {}).get("ref") or ""), tiers.tier, load
    )
    return Gate(tiers.tier, author, tiers.specialists, tuple(problems))


def evaluate(
    pr: dict[str, Any],
    sha: str,
    check_runs: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    workflow_runs: Sequence[dict[str, Any]] = (),
    gate: Gate | None = None,
) -> list[str]:
    """Reasons the PR may not merge at `sha`; an empty list means merge-ready."""
    gate = gate or Gate()
    return (
        head_reasons(pr, sha)
        + list(gate.problems)
        + check_reasons(check_runs, sha, workflow_runs, DOC_CHECK if gate.tier == 0 else GATE)
        + review_reasons(reviews, sha, gate)
    )


# ------------------------------------------------------------------ GitHub REST (I/O)
def _get(url: str) -> tuple[Any, str | None]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)  # noqa: S310 (https or local test stub)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        link = _NEXT.search(resp.headers.get("Link") or "")
        return json.load(resp), link.group(1) if link else None


def _all_pages(url: str, key: str | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    next_url: str | None = f"{url}{'&' if '?' in url else '?'}per_page=100"
    while next_url:
        body, next_url = _get(next_url)
        items.extend(body[key] if key else body)
    return items


def _optional(url: str) -> Any | None:
    """The JSON body at `url`, or None on 404 (the file is absent there)."""
    try:
        return _get(url)[0]
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _file(base: str, path: str, ref: str) -> bytes | None:
    """`path` at `ref` through the contents API, or None when it is absent there. A file the
    API returns without inline content (over 1 MB) raises, so the check fails closed."""
    quoted = urllib.parse.quote(path, safe="/")
    body = _optional(f"{base}/contents/{quoted}?ref={urllib.parse.quote(ref, safe='')}")
    if body is None:
        return None
    if body.get("encoding") != "base64":
        raise ValueError(f"{path}@{ref}: no inline content")
    try:
        return base64.b64decode(body["content"])
    except binascii.Error as exc:
        raise ValueError(f"{path}@{ref}: {exc}") from exc


def _text(data: bytes | None) -> str | None:
    try:
        return None if data is None else data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _tier_if(path: str, executable: bool) -> int:
    return file_tier(ChangedFile(path, executable, executable, False))[0]


def pr_files(base: str, pr: int, sha: str) -> list[ChangedFile]:
    """The PR's changed files for the classifier. A renamed file counts under both names. The
    executable bit, the shebang and a role file's front matter are read only where they can
    change the tier; a truncated tree counts as executable."""
    paths: dict[str, bool] = {}  # path -> present at the head
    for f in _all_pages(f"{base}/pulls/{pr}/files"):
        paths[f["filename"]] = f.get("status") != "removed"
        if f.get("previous_filename"):
            paths.setdefault(f["previous_filename"], False)
    tree: dict[str, str] | None = None
    merge_base: str | None = None
    files = []
    for path, present in paths.items():
        role_file = glob_match(AGENT_FILES, path)
        if not role_file and len({_tier_if(path, x) for x in (False, True)}) == 1:
            files.append(ChangedFile(path))  # the bit and the shebang cannot change its tier
            continue
        if tree is None:
            body, _ = _get(f"{base}/git/trees/{sha}?recursive=1")
            truncated = bool(body.get("truncated"))
            tree = {} if truncated else {e["path"]: e.get("mode", "") for e in body["tree"]}
            tree["\0truncated"] = "1" if truncated else ""
        head = _file(base, path, sha) if present else None
        executable = bool(tree["\0truncated"]) or tree.get(path) == "100755"
        front: bool | None = None
        if role_file:
            if merge_base is None:
                merge_base = _get(f"{base}/compare/main...{sha}")[0]["merge_base_commit"]["sha"]
            front = front_matter_changed(_text(_file(base, path, merge_base)), _text(head))
        files.append(ChangedFile(path, executable, (head or b"")[:2] == b"#!", front))
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True, help="OWNER/NAME")
    ap.add_argument("--pr", required=True, type=int)
    ap.add_argument("--sha", required=True, help="the PR head SHA to be merged")
    args = ap.parse_args(argv)
    api = (os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
    base = f"{api}/repos/{args.repo}"
    try:
        pr, _ = _get(f"{base}/pulls/{args.pr}")
        runs = _all_pages(f"{base}/commits/{args.sha}/check-runs", "check_runs")
        reviews = _all_pages(f"{base}/pulls/{args.pr}/reviews")
        wruns = _all_pages(f"{base}/actions/runs?head_sha={args.sha}", "workflow_runs")
        tiers = review_tier(pr_files(base, args.pr, args.sha))
        gate = gate_for(pr, tiers, lambda nn: _file(base, OWNERS.format(nn=nn), "main"))
    except (OSError, ValueError, KeyError, TypeError) as exc:  # URLError is an OSError
        print(f"merge-ready: unknown (GitHub could not be read: {exc})")
        return 2
    reasons = evaluate(pr, args.sha, runs, reviews, wruns, gate)
    for reason in reasons:
        print(f"- {reason}")
    flagged = ", ".join(sorted(gate.specialists)) or "none"
    print(f"review-tier: {gate.tier} (specialists: {flagged})")
    print(f"author-role: {gate.author or 'unknown'}")
    print(f"merge-ready: {'no' if reasons else 'yes'} (PR #{args.pr} at {args.sha})")
    return 1 if reasons else 0


if __name__ == "__main__":
    sys.exit(main())
