#!/usr/bin/env python3
"""Doc checks for the CI ``doc-check`` job (CI-DOC-CHECK; PRC-3.1-3.4; ADR 0056).

On the Markdown files a change adds or modifies (``--base``/``--head``), or on the files named:
1. PRC-3.1 every repo path a line names (a backticked path whose first part is a tracked top-level
   directory, or a relative Markdown link) exists at the head, from the repo root, from a
   subproject root (backend/, web/, infra/) or, for links, from the file's directory. In diff
   mode only added lines are checked. Placeholders (``<nn>``, ``*``, ``...``), git-ignored paths
   and lines marked ``(planned)`` are skipped;
2. PRC-3.2 every ``[ASB/<ID>]`` citation names a Confirmed row of the source register, unless
   ``(unverified)`` follows it on the same line (whole file);
3. PRC-3.3 every ``.claude/agents/*.md`` file opens with YAML front matter that parses to a
   mapping with non-empty ``name``, ``description`` and ``tools``;
4. PRC-3.4 ``docs/design/tools/check_flows.py --decider`` runs on the current sprint's flows file
   (``docs/design/flows-sprint-NN.md``, NN = newest ``docs/sprints/sprint-NN.md``) for every role
   row of its DR-NN decider table, whether or not the change touches it; skipped until it exists.
Exit 0 all pass; 1 at least one problem (one ``FAIL`` line each); 2 usage or git error.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

REGISTER = "docs/research/agentic-sdlc-best-practices.md"
FLOWS_TOOL = "docs/design/tools/check_flows.py"
SUBPROJECTS = ("backend", "web", "infra")
CODE = re.compile(r"`([^`\n]+)`")
LINK = re.compile(r"\]\(([^)\s]+)\)")
PLACEHOLDER = re.compile(r"[<>*{}$?\[\]|…]|\.\.\.")
SUFFIX = re.compile(r"(::.*|:\d+(?:[-,]\d+)*|#.*)$")
CITATION = re.compile(r"\[[^\]\n]*?ASB/[A-Z]+-\d+[^\]\n]*\]")
ASB_ID = re.compile(r"ASB/([A-Z]+-\d+)")
REGISTER_ROW = re.compile(r"^\| ASB/([A-Z]+-\d+) \|")
FIELDS = ("name", "description", "tools")


class GitError(Exception):
    pass


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if proc.returncode:
        raise GitError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout


def added_lines(root: Path, base: str, head: str) -> dict[str, set[int]]:
    """Changed ``*.md`` files (added, modified, renamed) mapped to their added line numbers."""
    diff = git(
        root, "diff", "-U0", "--no-color", "--diff-filter=AMR", f"{base}...{head}", "--", "*.md"
    )
    out: dict[str, set[int]] = {}
    current = None
    for ln in diff.splitlines():
        if ln.startswith("+++ "):
            current = ln[6:] if ln.startswith("+++ b/") else None
            if current:
                out.setdefault(current, set())
        elif ln.startswith("@@") and current:
            m = re.search(r"\+(\d+)(?:,(\d+))?", ln)
            if m:
                start, count = int(m.group(1)), int(m.group(2) or 1)
                out[current].update(range(start, start + count))
    return out


class Repo:
    def __init__(self, root: Path) -> None:
        self.root = root
        files = git(root, "ls-files").splitlines()
        self.tops = {f.split("/", 1)[0] for f in files if "/" in f}

    def exists(self, rel: str) -> bool:
        return any((self.root / p / rel).exists() for p in ("", *SUBPROJECTS))

    def ignored(self, rel: str) -> bool:
        cmd = ["git", "check-ignore", "-q", "--no-index", rel]
        return subprocess.run(cmd, cwd=self.root, capture_output=True).returncode == 0


def path_problems(repo: Repo, rel: str, n: int, line: str) -> list[str]:
    if "(planned)" in line:
        return []
    out = []
    for tok in CODE.findall(line):
        tok = tok.strip()
        if " " in tok or "/" not in tok or PLACEHOLDER.search(tok):
            continue
        path = SUFFIX.sub("", tok).rstrip("/")
        if path.split("/", 1)[0] not in repo.tops or repo.exists(path) or repo.ignored(path):
            continue
        out.append(f"FAIL path: {rel}:{n}: {path} does not exist")
    for target in LINK.findall(line):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue
        path = target.split("#", 1)[0]
        if PLACEHOLDER.search(path) or (repo.root / rel).parent.joinpath(path).exists():
            continue
        out.append(f"FAIL path: {rel}:{n}: {path} does not exist")
    return out


def load_register(root: Path) -> dict[str, str] | None:
    path = root / REGISTER
    if not path.is_file():
        return None
    status = {}
    for ln in path.read_text(encoding="utf-8").splitlines():
        m = REGISTER_ROW.match(ln)
        if m:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            status[m.group(1)] = cells[5] if len(cells) > 5 else ""
    return status


def citation_problems(register: dict[str, str], rel: str, n: int, line: str) -> list[str]:
    out = []
    for m in CITATION.finditer(line):
        if "(unverified)" in m.group(0) or "(unverified)" in line[m.end() :]:
            continue
        for sid in ASB_ID.findall(m.group(0)):
            status = register.get(sid)
            if status is None:
                out.append(f"FAIL citation: {rel}:{n}: ASB/{sid} is not in the register {REGISTER}")
            elif not status.startswith("Confirmed"):
                state = status.split(":", 1)[0]
                out.append(
                    f"FAIL citation: {rel}:{n}: ASB/{sid} is {state}; cite it with (unverified)"
                )
    return out


def front_matter_problems(rel: str, text: str) -> list[str]:
    head = f"FAIL front-matter: {rel}"
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return [f"{head} has no front matter (--- ... --- at the top)"]
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError as exc:
        return [f"{head} does not parse: {str(exc).splitlines()[0]}"]
    if not isinstance(data, dict):
        return [f"{head} is not a mapping"]
    return [f"{head} lacks {f}" for f in FIELDS if not str(data.get(f) or "").strip()]


def flows_problems(root: Path) -> tuple[list[str], list[str]]:
    """(problems, info lines) of check_flows.py --decider on the current sprint's flows file."""
    plans = sorted((root / "docs" / "sprints").glob("sprint-[0-9][0-9].md"))
    if not plans:
        return [], ["flows: no docs/sprints/sprint-NN.md; skipped (PRC-3.4)"]
    sprint = plans[-1].stem.split("-")[1]
    rel = f"docs/design/flows-sprint-{sprint}.md"
    if not (root / rel).is_file():
        return [], [f"flows: {rel} does not exist yet; skipped (PRC-3.4)"]
    review = f"DR-{sprint}"
    tool = root / FLOWS_TOOL
    sys.path.insert(0, str(tool.parent))
    try:
        import check_flows  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)
    table = check_flows._review_table((root / rel).read_text(encoding="utf-8"), review)
    label = f"{rel} --review {review}"
    if isinstance(table, str):
        return [f"FAIL flows: {label}: {table}"], []
    roles = sorted({row[0] for row in table[1] if row and row[0]})
    if not roles:
        return [f"FAIL flows: {label}: the decider table has no role rows"], []
    args = [a for role in roles for a in ("--decider", role)]
    proc = subprocess.run(
        [sys.executable, str(tool), str(root / rel), "--review", review, *args],
        capture_output=True,
        text=True,
    )
    info = f"flows: {label} {' '.join(args)}: rc {proc.returncode}"
    if proc.returncode == 0:
        return [], [info]
    fails = [ln for ln in proc.stdout.splitlines() if ln.startswith("FAIL")] or [
        proc.stderr.strip()
    ]
    return [f"FAIL flows: {label}: {ln}" for ln in fails], [info]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("files", nargs="*", help="Markdown files to check whole (default: the diff)")
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--base", help="base ref; only lines the change adds are path-checked")
    p.add_argument("--head", default="HEAD")
    a = p.parse_args(argv)
    root = a.root.resolve()
    targets: dict[str, set[int] | None]
    try:
        root = Path(git(root, "rev-parse", "--show-toplevel").strip())
        if a.files:
            targets = dict.fromkeys(a.files)
        else:
            base = a.base or f"{a.head}^"
            targets = {f: set(n) for f, n in added_lines(root, base, a.head).items()}
        repo = Repo(root)
    except GitError as exc:
        print(f"doc-check: {exc}", file=sys.stderr)
        return 2

    register = load_register(root)
    problems: list[str] = []
    if register is None:
        problems.append(f"FAIL citation: register {REGISTER} not found")
    for rel, lines in sorted(targets.items()):
        path = root / rel
        if not path.is_file():
            problems.append(f"FAIL path: {rel} does not exist")
            continue
        text = path.read_text(encoding="utf-8")
        for n, line in enumerate(text.splitlines(), 1):
            if lines is None or n in lines:
                problems += path_problems(repo, rel, n, line)
            problems += citation_problems(register or {}, rel, n, line)
        if re.fullmatch(r"\.claude/agents/[^/]+\.md", rel):
            problems += front_matter_problems(rel, text)
    flow_fails, info = flows_problems(root)
    problems += flow_fails
    print("\n".join([*info, *problems]))
    print(f"doc-check: {len(problems)} problem(s) in {len(targets)} file(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
