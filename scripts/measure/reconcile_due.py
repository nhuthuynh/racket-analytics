#!/usr/bin/env python3
"""Open review-rounds rows that a merged ticket names or whose evidence it changed (FIX-03-1a).

    reconcile_due.py docs/sprints/03/review-rounds.md \
        --plan docs/decisions/0039-*.md --decisions docs/sprints/03/decisions \
        --base origin/main [--report-only] [--json out.json]

A ticket PR that closes a finding writes no review-rounds row, so ``open_defects.py`` keeps
counting the finding as open after the ticket merged (V03R1-01, goal scorecard G03-12). This
check lists every open blocker/major row (as ``open_defects.py`` reads it) that a merged ticket
names: a commit of the ADR 0039 per-ticket plan whose subject scope names one of the row's ids,
or a ticket decisions file ``<id>.md`` / ``<id>-*.md`` that is on the base branch (``--base``,
a git ref): a ticket PR adds its own decisions file before it merges, so a file only on the PR's
head names no merged ticket (PE-FIX031A-01). Without ``--base`` every file counts. The row is
reconciled once its latest row, or that row's section heading, names the ticket, its PR
(``#n``) or its merge commit.

With ``--base`` a row is also due when a ticket PR merged into the base (a GitHub merge commit
"Merge pull request #n from ...", ticket = the ``[TICKET]`` of its title) after the row's latest
line was last written (``git blame``; a row not yet committed is newer than every merge; the
merge of the PR that wrote the row is not later than it) changes a file that the row's Evidence
cell cites, or names one of the row's ids in its PR title (C4-RECON, VM-R3-02: FIX-03-2b named
PE-PR24-01 and FIX-03-2c changed `sprint-03.md`, which an open row cited, and the check said
"0 due"). The ledger file itself is never evidence: writing it is the reconciliation.

Exit 0 when nothing is due, 1 when a row is due (the engineering-manager writes the row), 2 on
a usage error (no review table, unreadable plan or decisions dir, a base or ledger git cannot
read; fail closed, ADR 0014). ``--report-only`` prints the due rows but exits 0 for them (usage
errors still exit 2): CI runs it that way on the live ledger, because on a push to main the base
is main itself and a just-merged fix ticket's row stays due until the EM writes it; that is EM
work, not a red main (PE-FIX031A-03). The EM status step runs the check without it.
Limit: a finding closed by work that names no id and changes no cited file is not seen.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measurelib import _FINDING_ID, _cells, open_defects

_SHA = re.compile(r"`?([0-9a-f]{7,40})`?")
_PR = re.compile(r"#(\d+)\b")
_COMMIT_ROW = re.compile(r"^\|\s*\d+\s*\|\s*`[0-9a-f]{7,40}`\s*\|")
_TOKEN = re.compile(r"[A-Za-z0-9_.*/-]+")
_FILE = re.compile(
    r"[\w*-]+(?:\.[\w*-]+)*\.(?:md|py|json|ya?ml|feature|toml|sql|tsx?|js|sh|txt|csv|lock)"
)
_GITHUB_MERGE = re.compile(r"Merge pull request #(\d+) from [^/\s]+/(\S+)")
_TITLE_TICKET = re.compile(r"\s*\[([^\]]+)\]")
_NO_COMMIT = re.compile(r"0{40}")
_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


def _merged_prs(plan_text: str) -> dict[str, dict[str, str]]:
    """Ticket -> {pr, merged_as} from the plan's PR table (header names "Merged")."""
    prs: dict[str, dict[str, str]] = {}
    header: list[str] | None = None
    for line in plan_text.splitlines():
        if not line.lstrip().startswith("|"):
            header = None
            continue
        cells = _cells(line)
        if header is None:
            header = [c.lower() for c in cells]
            continue
        merged = next((i for i, h in enumerate(header) if h.startswith("merged")), None)
        if merged is None or "pr" not in header or set("".join(cells)) <= set("-: "):
            continue
        pr, sha = cells[header.index("pr")], _SHA.search(cells[merged])
        if _PR.fullmatch(pr) and sha:
            prs[cells[0]] = {"pr": pr, "merged_as": sha.group(1)}
    return prs


def ticket_index(plan_text: str, decision_stems: list[str]) -> list[dict[str, Any]]:
    """Every merged ticket with the finding ids it names (commit scopes) or is named after."""
    prs = _merged_prs(plan_text)
    tickets: dict[str, dict[str, Any]] = {}

    def add(ticket: str, pr: str | None, names: set[str], prefix: str | None = None) -> None:
        entry = tickets.setdefault(
            ticket,
            {
                "ticket": ticket,
                "pr": pr or prs.get(ticket, {}).get("pr"),
                "merged_as": prs.get(ticket, {}).get("merged_as"),
                "names": set(),
                "prefixes": set(),
            },
        )
        entry["names"] |= names
        if prefix:
            entry["prefixes"].add(prefix)

    for line in plan_text.splitlines():
        if not _COMMIT_ROW.match(line):
            continue
        cells = _cells(line)
        scope = re.search(r"\(([^)]*)\)", cells[2])
        pr = _PR.search(cells[3])
        if not scope or not pr:
            continue  # a commit with no ticket PR is not a merged ticket
        ticket = cells[3].split("(")[0].strip()
        add(ticket, f"#{pr.group(1)}", {s.strip() for s in scope.group(1).split(",")})
    for stem in decision_stems:
        add(stem, None, set(), prefix=stem)
    return [
        {**t, "names": sorted(t["names"]), "prefixes": sorted(t["prefixes"])}
        for t in tickets.values()
    ]


def _names(ticket: dict[str, Any], finding: str) -> bool:
    if finding in ticket["names"]:
        return True
    return any(p == finding or p.startswith(finding + "-") for p in ticket["prefixes"])


def _mentions(text: str, ticket: dict[str, Any]) -> bool:
    words = [re.escape(ticket["ticket"])]
    if ticket["pr"]:
        words.append(re.escape(ticket["pr"]) + r"(?!\d)")
    if ticket["merged_as"]:
        words.append(re.escape(ticket["merged_as"][:7]))
    edge = r"(?<![A-Za-z0-9-]){}(?![A-Za-z0-9-])"
    return any(re.search(edge.format(w), text) for w in words)


def _row_context(lines: list[str], number: int) -> tuple[str, str]:
    """The row's text without its finding-id cell, and the heading of its section."""
    context = " | ".join(_cells(lines[number - 1])[1:])  # never the finding-id cell itself
    heading = next((lines[i] for i in range(number - 1, -1, -1) if lines[i].startswith("#")), "")
    return context, heading


def due_rows(ledger_text: str, tickets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Open blocker/major rows named by a ticket that neither the row nor its heading names."""
    lines = ledger_text.splitlines()
    due = []
    for row in open_defects(ledger_text):
        context, heading = _row_context(lines, row["line"])
        named = [
            t
            for t in tickets
            if any(_names(t, f) for f in row["ids"])
            and not _mentions(context, t)
            and not _mentions(heading, t)
        ]
        if named:
            due.append({**row, "tickets": named})
    return due


def evidence_paths(cell: str) -> list[str]:
    """The file paths (``a/b.md``, ``0039-*.md``, ``sprint-03.md``) an Evidence cell cites."""
    paths = []
    for token in _TOKEN.findall(cell):
        token = token.strip(".-/")
        if not re.search(r"[A-Za-z]", token) or "//" in token:
            continue
        if "/" in token or _FILE.fullmatch(token):
            paths.append(token)
    return list(dict.fromkeys(paths))


def title_ids(body: str) -> list[str]:
    """The finding ids a merge's PR title (first body line) names, without its own ``[TICKET]``."""
    title = body.strip().splitlines()[0] if body.strip() else ""
    title = _TITLE_TICKET.sub("", title, count=1)
    return list(dict.fromkeys(_FINDING_ID.findall(title)))


def cited_changes(changed: list[str], cited: list[str]) -> list[str]:
    """The changed repo paths that a cited path names (whole path, path suffix, or glob)."""
    return [
        f
        for f in changed
        if any(fnmatch.fnmatchcase(f, p) or fnmatch.fnmatchcase(f, "*/" + p) for p in cited)
    ]


def parse_merges(log: str) -> list[dict[str, Any]]:
    """GitHub ticket PR merges from ``MergeHistory.merges_after``'s ``git log``; other merges
    (no "Merge pull request #n from ...") are not ticket PRs and are skipped."""
    merges = []
    for record in log.split("\x1e"):
        head, _, names = record.partition("\x1d")
        parts = head.split("\x1f", 2)
        if len(parts) != 3:
            continue
        sha, subject, body = parts
        merge = _GITHUB_MERGE.match(subject.strip())
        if not merge:
            continue
        title = _TITLE_TICKET.match(body)
        merges.append(
            {
                "ticket": title.group(1).strip() if title else merge.group(2),
                "pr": f"#{merge.group(1)}",
                "merged_as": sha.strip(),
                "changed": [n.strip() for n in names.splitlines() if n.strip()],
                "title_ids": title_ids(body),
            }
        )
    return merges


def _row_cells(line: str) -> list[str]:
    return [c.strip() for c in _UNESCAPED_PIPE.split(line.strip().strip("|"))]


def _evidence_cell(lines: list[str], number: int) -> str:
    """The Evidence cell of the table row at 1-based line ``number`` ("" when none).

    Cells split on unescaped pipes only: an evidence command often carries ``\\|``.
    """
    top = number - 1
    while top > 0 and lines[top - 1].lstrip().startswith("|"):
        top -= 1
    header = [h.lower() for h in _row_cells(lines[top])]
    col = next((i for i, h in enumerate(header) if "evidence" in h), None)
    cells = _row_cells(lines[number - 1])
    return cells[col] if col is not None and col < len(cells) else ""


def evidence_due(
    ledger_text: str,
    rows: list[dict[str, Any]],
    merges_after: Callable[[int], list[dict[str, Any]]],
    ledger_path: str,
) -> list[dict[str, Any]]:
    """Open rows that a merge after their latest line bears on (VM-R3-02): its diff changes a
    file the row's Evidence cell cites, or its PR title names one of the row's ids.

    ``merges_after(line)`` gives the ticket PR merges later than that ledger line's last write.
    A merge the row or its heading names (ticket, ``#n`` or sha) is already reconciled.
    """
    lines = ledger_text.splitlines()
    due = []
    for row in rows:
        cited = evidence_paths(_evidence_cell(lines, row["line"]))
        context, heading = _row_context(lines, row["line"])
        hits = []
        for merge in merges_after(row["line"]):
            changed = cited_changes([f for f in merge["changed"] if f != ledger_path], cited)
            named = [f for f in row["ids"] if f in merge["title_ids"]]
            if (changed or named) and not (_mentions(context, merge) or _mentions(heading, merge)):
                hits.append({**merge, "changed": changed, "title_ids": named})
        if hits:
            due.append({**row, "evidence": hits})
    return due


def _git(repo: Path, *args: str) -> str:
    argv = ["git", "-C", str(repo), "-c", "core.quotePath=false", *args]
    out = subprocess.run(  # noqa: S603 - fixed argv, no shell; refs are checked by the caller
        argv,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if out.returncode != 0:
        raise ValueError(f"git {args[0]} in {repo}: {out.stderr.strip()}")
    return out.stdout


class MergeHistory:
    """The ticket PR merges on ``base`` later than each ledger line (git blame of the file)."""

    def __init__(self, ledger: Path, base: str) -> None:
        if base.startswith("-"):
            raise ValueError(f"not a git ref: {base}")
        self.dir = ledger.resolve().parent
        top = Path(_git(self.dir, "rev-parse", "--show-toplevel").strip()).resolve()
        self.path = ledger.resolve().relative_to(top).as_posix()
        self.name = ledger.name
        self.base = f"{base}^{{commit}}"
        self.tracked = bool(_git(self.dir, "ls-files", "--", self.name).strip())
        _git(self.dir, "rev-parse", "--verify", "--quiet", self.base)

    def last_written(self, line: int) -> str | None:
        """The commit that last wrote ``line``; None when the line is not committed yet."""
        if not self.tracked:
            return None  # a ledger never committed: every line is newer than every merge
        out = _git(self.dir, "blame", "--porcelain", "-L", f"{line},{line}", "--", self.name)
        sha = out.split(" ", 1)[0]
        return None if _NO_COMMIT.fullmatch(sha) else sha

    def merges_after(self, line: int) -> list[dict[str, Any]]:
        since = self.last_written(line)
        if since is None:
            return []
        log = _git(
            self.dir,
            "log",
            "--first-parent",
            "--merges",
            "--diff-merges=first-parent",
            "--name-only",
            "--format=%x1e%H%x1f%s%x1f%b%x1d",
            self.base,
            f"^{since}",
            "--",
        )
        own = self.merged_in(since)
        return [m for m in parse_merges(log) if m["merged_as"] != own]

    def merged_in(self, commit: str) -> str | None:
        """The first-parent merge on the base that brought ``commit`` in (the row's own PR).

        None when ``commit`` is on the base's first-parent line itself or not on the base.
        """
        path = _git(
            self.dir, "rev-list", "--first-parent", "--ancestry-path", f"{commit}..{self.base}"
        ).split()
        if not path:
            return None
        first = path[-1]  # the oldest first-parent descendant of the row's commit
        return None if self.is_ancestor(commit, f"{first}^1") else first

    def is_ancestor(self, commit: str, of: str) -> bool:
        argv = ["git", "-C", str(self.dir), "merge-base", "--is-ancestor", commit, of]
        out = subprocess.run(argv, capture_output=True, text=True, timeout=60)  # noqa: S603
        if out.returncode not in (0, 1):
            raise ValueError(f"git merge-base in {self.dir}: {out.stderr.strip()}")
        return out.returncode == 0


def _merge_rows(
    named: list[dict[str, Any]], evidence: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """One entry per due row, with the naming tickets and the evidence-changing merges."""
    rows: dict[int, dict[str, Any]] = {}
    for row in named:
        rows[row["line"]] = {**row, "evidence": []}
    for row in evidence:
        rows.setdefault(row["line"], {**row, "tickets": []})["evidence"] = row["evidence"]
    return [rows[k] for k in sorted(rows)]


def decision_stems(decisions: Path, base: str | None) -> list[str]:
    """Stems of the ``*.md`` ticket decisions files; with ``base``, only those on that ref."""
    if not decisions.is_dir():
        raise ValueError(f"not a directory: {decisions}")
    names = {p.name for p in decisions.glob("*.md")}
    if base is not None:
        if base.startswith("-"):
            raise ValueError(f"not a git ref: {base}")
        argv = ["git", "-C", str(decisions), "ls-tree", "--name-only", f"{base}^{{commit}}", "."]
        out = subprocess.run(  # noqa: S603 - fixed argv, no shell; base is the caller's own ref
            argv,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if out.returncode != 0:
            raise ValueError(f"cannot list {decisions} at base {base}: {out.stderr.strip()}")
        names &= set(out.stdout.splitlines())
    return sorted(n[: -len(".md")] for n in names)


def exit_status(due: int, *, report_only: bool) -> int:
    """1 when a row is due, unless only reporting; usage errors are handled before this."""
    return 1 if due and not report_only else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ledger", type=Path, help="review-rounds Markdown file")
    parser.add_argument("--plan", type=Path, help="ADR with the per-ticket plan (ADR 0039)")
    parser.add_argument("--decisions", type=Path, help="the sprint's ticket decisions dir")
    parser.add_argument("--base", help="git ref; only decisions files on it count (merged)")
    parser.add_argument(
        "--report-only", action="store_true", help="print due rows but exit 0 for them"
    )
    parser.add_argument("--json", type=Path, help="also write the result here")
    args = parser.parse_args(argv)
    try:
        text = args.ledger.read_text(encoding="utf-8")
        plan_text = args.plan.read_text(encoding="utf-8") if args.plan else ""
        stems = decision_stems(args.decisions, args.base) if args.decisions else []
        open_rows = open_defects(text)
        due = due_rows(text, ticket_index(plan_text, stems))
        if args.base is not None:
            history = MergeHistory(args.ledger, args.base)
            changed = evidence_due(text, open_rows, history.merges_after, history.path)
            due = _merge_rows(due, changed)
    except (OSError, ValueError) as exc:
        print(f"reconcile-due: {exc}", file=sys.stderr)
        return 2
    for row in due:
        ids = " / ".join(row["ids"])
        if row.get("tickets"):
            named = "; ".join(
                f"ticket {t['ticket']}"
                + (f" ({t['pr']})" if t["pr"] else "")
                + (f" merged as {t['merged_as']}" if t["merged_as"] else "")
                for t in row["tickets"]
            )
            print(f"due: line {row['line']}: {ids} ({row['severity']}) named by {named}")
        for m in row.get("evidence", []):
            merge = f"ticket {m['ticket']} ({m['pr']}) merged as {m['merged_as'][:7]}"
            due_row = f"due: line {row['line']}: {ids} ({row['severity']})"
            if m["title_ids"]:
                print(f"{due_row} named by the PR title of {merge}")
            if m["changed"]:
                print(f"{due_row} evidence changed by {merge} ({', '.join(m['changed'])})")
    open_count = len(open_rows)
    print(f"reconcile-due: {open_count} open blocker/major rows, {len(due)} due")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        result = {"open": open_count, "due": len(due), "rows": due}
        args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return exit_status(len(due), report_only=args.report_only)


if __name__ == "__main__":
    sys.exit(main())
