"""Test support for C4-RECON (VM-R3-02): a throwaway repo whose main merges ticket PRs.

The repo holds a review-rounds ledger with an Evidence column and the files that evidence cites.
``merge_ticket`` merges a ticket branch the way GitHub does ("Merge pull request #n from ..."
with the PR title "[TICKET] ..." in the body), so ``reconcile_due.py --base main`` sees it.
"""

from __future__ import annotations

from pathlib import Path

from reconcile_ledger import git

LEDGER = Path("docs/sprints/99/review-rounds.md")
DECISIONS = Path("docs/sprints/99/decisions")
EVIDENCE_HEAD = "| Finding | Severity | Disposition | Owner | Evidence |\n|---|---|---|---|---|\n"


def evidence_section(heading: str, rows: list[tuple[str, str, str, str]]) -> str:
    """``rows``: (finding ids, severity, disposition, evidence cell)."""
    body = "".join(f"| {f} | {s} | {d} | owner | {e} |\n" for f, s, d, e in rows)
    return f"## {heading}\n\n{EVIDENCE_HEAD}{body}\n"


def open_row(finding: str, cited: str) -> str:
    return evidence_section(
        "Sprint 99 close",
        [(finding, "major", "**Open.** waits on the owner", f"`sed -n 3p {cited}`")],
    )


def init_main(repo: Path, ledger_text: str, files: list[str]) -> None:
    """Commit the ledger, an empty decisions dir and ``files`` as the first commit of ``main``."""
    for name in files:
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text("v1\n", encoding="utf-8")
    (repo / DECISIONS).mkdir(parents=True, exist_ok=True)
    (repo / DECISIONS / "OTHER-1.md").write_text("# d\n", encoding="utf-8")
    (repo / LEDGER).write_text(ledger_text, encoding="utf-8")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")


def merge_ticket(
    repo: Path, ticket: str, pr: int, changes: list[str], title: str = "change evidence"
) -> str:
    """Merge a ticket branch that edits ``changes`` into ``main``; return the merge commit sha."""
    branch = f"s99/{ticket.lower()}"
    git(repo, "checkout", "-q", "-b", branch)
    for name in changes:
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        with (repo / name).open("a", encoding="utf-8") as fh:
            fh.write(f"changed by {ticket}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"docs({ticket}): change evidence")
    git(repo, "checkout", "-q", "main")
    git(
        repo,
        "merge",
        "-q",
        "--no-ff",
        branch,
        "-m",
        f"Merge pull request #{pr} from owner/{branch}",
        "-m",
        f"[{ticket}] {title}",
    )
    return git(repo, "rev-parse", "HEAD").strip()


def append_ledger(repo: Path, text: str, *, commit: bool = True) -> None:
    with (repo / LEDGER).open("a", encoding="utf-8") as fh:
        fh.write("\n" + text)
    if commit:
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "em: reconciliation row")
