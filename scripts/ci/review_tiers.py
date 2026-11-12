#!/usr/bin/env python3
"""Review tier of a pull request from its changed paths (CI-TIERS-a; ADR 0056; PRC-2.1-2.3).

Tier 0 is docs and process text, tier 1 ordinary code, tier 2 security, personal data, schema,
API contracts and the merge gate itself (kickoff SEC-1). The rules are data (`RULES`) and have no
order: a file gets the HIGHEST tier of every rule it matches, so a broader rule never lowers a
tier; the PR gets the highest tier over its files; a path that matches no rule, or an empty
change set, is tier 2 (fail closed). An executable file is at least tier 1 wherever it lives
(`EXEC_*`, a shebang line or the executable bit); one that no rule names is tier 1 under `docs/`
and tier 2 elsewhere (CI-TIERS-b, sprint-05 §7 "an unclassified path is tier 2").
A `.claude/agents/*.md` file whose front matter (the text between its first two `---` lines;
lines end at "\n" only) differs between the merge base and head is tier 2, as is an added or
deleted role file, one without a closed front matter block, one whose front matter holds a
control character or U+2028/U+2029, and one whose front matter state the caller did not
compute: the only rule that reads content, not just the path (separation of duties, audit
item 13).
The tier is always computed here, never read from a label or the PR body.
`merge_ready.py` imports this module and maps the tier to the required verdicts (CI-TIERS-b);
it reads `BOOTSTRAP_OWNERS` before `docs/sprints/<nn>/ticket-owners.json` for the author role.

Usage: review_tiers.py --base REF --head REF [--json]   (in a git checkout; prints the tier,
the flagged specialist roles and each file's tier). Exit 0, or 2 when git cannot be read.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import PurePosixPath

DESIGNER = "principal-designer"
COACH = "pickleball-domain-coach"
ML = "senior-ml-cv-engineer"
FRONTEND = "senior-frontend-engineer"
FAIL_CLOSED = 2


@dataclass(frozen=True)
class Rule:
    glob: str
    tier: int
    roles: tuple[str, ...] = ()


# Kickoff SEC-1 / PRC-2.3. Each glob must match a tracked path (test_every_tier2_glob_...).
_TIER2 = (
    # auth and identity
    "backend/src/racket/players/**",
    "web/src/lib/auth/**",
    "web/src/app/auth/**",
    "web/src/components/AuthCallback.tsx",
    "web/src/lib/session/**",
    # uploads (video_ingest), storage, media URLs, quotas
    "backend/src/racket/video_ingest/**",
    "web/src/lib/upload/**",
    "backend/src/racket/platform/storage.py",
    "web/src/lib/api/storage-quota.ts",
    "web/src/lib/media/**",
    "backend/src/racket/platform/ratelimit.py",
    "web/src/lib/api/quota.ts",
    # privacy, age, consent, retention, deletion
    "backend/src/racket/*/deletion.py",
    "backend/src/racket/platform/purge.py",
    "infra/docker/purge_schedule.py",
    "web/src/lib/identity/**",
    "web/src/lib/api/age-gate.ts",
    "web/src/components/age/**",
    "web/src/app/welcome/age/**",
    "web/src/components/settings/Privacy*",
    "web/src/app/settings/privacy/**",
    # logging config and secrets
    "backend/src/racket/platform/logs.py",
    "backend/src/racket/platform/settings.py",
    "backend/src/racket/platform/fault*",  # the ADR 0012 API fault seam (ST-075d, T5-OB-5)
    "infra/compose.fault-drill.yaml",  # turns the fault seam on for the drill (ST-075c, T5-OB-5)
    "infra/env.example",
    "infra/tls/**",
    ".gitleaks.toml",
    ".gitleaksignore",
    ".claude/settings.json",
    ".claude/hooks/**",  # pre_tool_use.py refuses writes to secret paths (SEC-188-03)
    # client security (also flags the frontend engineer below)
    "web/src/lib/security/**",
    "web/src/middleware.ts",
    # CI permissions, schema, API contracts, the merge gate and its only author-role input
    ".github/workflows/**",
    "backend/src/racket/migrations/**",
    "docs/architecture/api-*.md",
    "docs/sprints/*/ticket-owners.json",
    "scripts/ci/merge_ready.py",
    "scripts/ci/review_tiers.py",
)

# A tier 2 glob whose path a named ticket creates. Classified like `RULES`; exempt from the
# liveness test until it matches, then it must move into `_TIER2` (the test fails until it does).
PENDING_GLOBS: dict[str, str] = {}

_TIER1 = (
    "backend/**",
    "web/**",
    "infra/**",
    "scripts/**",
    "tests/**",
    "content/**",
    "fixtures/**",
    ".github/**",
    "docs/security/tools/**",
    "docs/design/tools/**",
    "docs/domain/tools/**",
    "docs/sprints/*/close-checks/**",
    "Makefile",
    "ruff.toml",
    ".gitignore",
    ".dockerignore",
)

# Specialist flags only add roles; a path's tier still comes from the tier 0/1/2 tables above.
_SPECIALISTS = (
    Rule("web/src/app/**", 1, (DESIGNER,)),
    Rule("web/src/components/**", 1, (DESIGNER,)),
    Rule("web/src/**/*.css", 1, (DESIGNER,)),
    Rule("web/public/**", 1, (DESIGNER,)),
    Rule("backend/src/racket/coaching/drills/**", 1, (COACH,)),
    Rule("content/drills/**", 1, (COACH,)),
    Rule("backend/src/racket/sports/**", 1, (COACH,)),
    Rule("backend/src/racket/matches/scorebook/**", 1, (COACH,)),
    Rule("backend/src/racket/worker/**", 1, (ML,)),
    Rule("backend/src/racket/dataset/**", 1, (ML,)),
    Rule("backend/src/racket/**/evals/**", 1, (ML,)),
    Rule("web/src/lib/security/**", 1, (FRONTEND,)),
    Rule("web/src/middleware.ts", 1, (FRONTEND,)),
    Rule("web/next.config.ts", 1, (FRONTEND,)),
    Rule("web/public/sw.js", 1, (FRONTEND,)),
)

EM, SRE = "engineering-manager", "sre-devops-engineer"
# CI-TIERS-b bootstrap (PE-PLAN05-R3-01): head-branch shapes whose author role is fixed here,
# read by merge_ready.py BEFORE docs/sprints/<nn>/ticket-owners.json, for PRs that cannot have a
# row on main yet: (regex over the whole head branch, owner role, highest tier it may carry or
# None). An optional "-<slug>" suffix follows the id, as on every lane branch.
BOOTSTRAP_OWNERS: tuple[tuple[str, str, int | None], ...] = (
    (r"s(?P<nn>\d{2})/plan(?:-[a-z0-9][a-z0-9-]*)?", EM, None),  # creates the owner file
    (r"s(?P<nn>\d{2})/ci-fix-[a-z0-9][a-z0-9-]*", SRE, None),  # CI FIRST red-main fix
    (r"s(?P<nn>\d{2})/owners-[a-z0-9][a-z0-9-]*", EM, None),  # adds a mid-sprint row
    (r"docs/[a-z0-9][a-z0-9-]*", EM, 0),  # docs and process text only
)

AGENT_FILES = ".claude/agents/*.md"
_TIER0 = ("docs/**/*.md", "*.md", AGENT_FILES, "docs/sprints/*/status.json")

RULES: tuple[Rule, ...] = (
    *(Rule(g, 0) for g in _TIER0),
    *(Rule(g, 1) for g in _TIER1),
    *(Rule(g, 2) for g in _TIER2),
    *_SPECIALISTS,
)

EXEC_SUFFIXES = (".py", ".sh", ".js", ".mjs", ".ts", ".tsx", ".sql")
_FENCE = "---"


@dataclass(frozen=True)
class ChangedFile:
    path: str
    executable: bool = False  # the executable bit in the PR's tree
    shebang: bool = False  # the file starts with "#!"
    # Only read for .claude/agents/*.md: None (not computed, e.g. no blobs) is tier 2 there.
    front_matter_changed: bool | None = None


@dataclass(frozen=True)
class Classification:
    tier: int
    specialists: frozenset[str]
    files: Mapping[str, int]


@cache
def _regex(glob: str) -> re.Pattern[str]:
    out, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def glob_match(glob: str, path: str) -> bool:
    """`*` and `?` stay inside one path segment; `**` crosses segments (`**/` may be empty)."""
    return _regex(glob).match(path) is not None


def is_executable(f: ChangedFile) -> bool:
    name = PurePosixPath(f.path).name
    return (
        f.executable
        or f.shebang
        or f.path.endswith(EXEC_SUFFIXES)
        or f.path.startswith(".github/workflows/")
        or name == "Makefile"
        or name.startswith("Dockerfile")
        or name.endswith(".Dockerfile")
    )


def _matches(path: str, rules: Sequence[Rule]) -> list[Rule]:
    pending = (Rule(g, 2) for g in PENDING_GLOBS)
    return [r for r in (*rules, *pending) if glob_match(r.glob, path)]


def file_tier(f: ChangedFile, rules: Sequence[Rule] = RULES) -> tuple[int, frozenset[str]]:
    """(tier, specialist roles) of one changed file: the highest matching rule, tier 2 when
    none matches, raised to 1 for an executable file and to 2 for a role file's front matter."""
    hits = _matches(f.path, rules)
    # The executable floor counts as a matched tier 1 rule under docs/ (a shebang script there
    # is tier 1); any other file no rule names fails closed, code included (CI-TIERS-b, §7).
    floor = is_executable(f) and (bool(hits) or f.path.startswith("docs/"))
    tiers = [r.tier for r in hits] + ([1] if floor else [])
    tier = max(tiers, default=FAIL_CLOSED)
    if f.front_matter_changed is not False and glob_match(AGENT_FILES, f.path):
        tier = 2  # changed, or unknown (SEC-188-07): fail closed
    return tier, frozenset(role for r in hits for role in r.roles)


def classify(files: Iterable[ChangedFile], rules: Sequence[Rule] = RULES) -> Classification:
    """The PR's tier is the highest over its files; no changed file at all fails closed."""
    tiers: dict[str, int] = {}
    roles: set[str] = set()
    for f in files:
        tiers[f.path], flagged = file_tier(f, rules)
        roles |= flagged
    return Classification(max(tiers.values(), default=FAIL_CLOSED), frozenset(roles), tiers)


def _unsafe(ch: str) -> bool:
    """A C0/C1 control character other than tab, DEL, or U+2028/U+2029: a line break to some
    reader but not to another (PE-CITA-05, SEC-188-06). Other non-ASCII text (`§`) is fine."""
    return ch != "\t" and unicodedata.category(ch) in ("Cc", "Zl", "Zp")


def _front_matter(text: str) -> list[str] | None:
    """The lines between the first line `---` and the next `---` line, or None when the file
    does not start with `---`, the block is never closed, or the block holds an unsafe
    character. Lines end at "\n" only, with one trailing "\r" dropped, as a newline-based
    reader and a YAML 1.2 parser read them; `str.splitlines()` also breaks at VT, FF, FS-RS,
    NEL, U+2028, U+2029 and a lone CR, which let a fake closing fence hide new keys."""
    lines = [line.removesuffix("\r") for line in text.split("\n")]
    if lines[0] != _FENCE or _FENCE not in lines[1:]:
        return None
    block = lines[1 : lines.index(_FENCE, 1)]
    if any(_unsafe(ch) for line in block for ch in line):
        return None
    return block


def front_matter_changed(base: str | None, head: str | None) -> bool:
    """True when a role file's front matter text differs between the base and head blobs. Any
    key can change a role's powers (`tools`, a block-list item or a continuation line under it,
    `permissionMode`, `mcpServers`, `hooks`, `skills`, a removed `disallowedTools`), so any
    change counts. An added or deleted file (a side is None) and a side without a closed front
    matter block fail closed (PE-CITA-01, SEC-188-01, SEC-188-02)."""
    if base is None or head is None:
        return True
    old, new = _front_matter(base), _front_matter(head)
    return old is None or new is None or old != new


def dead_tier2_globs(
    tracked: Iterable[str],
    rules: Sequence[Rule] = RULES,
    pending: Mapping[str, str] = PENDING_GLOBS,
) -> list[str]:
    """One message per tier 2 glob that matches no tracked path, per pending glob that now
    matches one (move it into the rules), and per pending glob that names no creating ticket."""
    paths = list(tracked)
    problems = []
    for glob in dict.fromkeys(r.glob for r in rules if r.tier == 2):
        if not any(glob_match(glob, p) for p in paths):
            problems.append(f"tier 2 glob {glob!r} matches no tracked path")
    for glob, ticket in pending.items():
        if not ticket.strip():
            problems.append(f"pending glob {glob!r} names no creating ticket")
        elif any(glob_match(glob, p) for p in paths):
            problems.append(f"pending glob {glob!r} ({ticket}) now matches; move it into RULES")
    return problems


# ------------------------------------------------------------------ git (I/O)
def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout


def _blob_text(rev: str, path: str) -> str | None:
    """`path` at `rev` as text, or None when it is absent there or is not UTF-8."""
    proc = subprocess.run(["git", "cat-file", "blob", f"{rev}:{path}"], capture_output=True)
    if proc.returncode != 0:
        return None
    try:
        return proc.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None


def changed_files(base: str, head: str) -> list[ChangedFile]:
    """The PR's changed files (merge base of `base` to `head`), with the executable bit and the
    shebang read from `head`'s tree and, for role files, whether the front matter changed
    between the merge base blob and the head blob."""
    rng = f"{base}...{head}"
    merge_base = _git("merge-base", base, head).decode().strip()
    paths = [
        p for p in _git("diff", "--name-only", "--no-renames", "-z", rng).decode().split("\0") if p
    ]
    files = []
    for path in paths:
        entry = _git("ls-tree", "-z", head, "--", path).decode()
        mode = entry.split(" ", 1)[0] if entry else ""
        head_bytes = (
            _git("cat-file", "blob", f"{head}:{path}")[:2] if mode.startswith("100") else b""
        )
        front = glob_match(AGENT_FILES, path) and front_matter_changed(
            _blob_text(merge_base, path), _blob_text(head, path)
        )
        files.append(ChangedFile(path, mode == "100755", head_bytes == b"#!", front))
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--json", action="store_true", help="print one JSON object")
    args = ap.parse_args(argv)
    try:
        result = classify(changed_files(args.base, args.head))
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"review-tier: unknown (git could not be read: {exc})", file=sys.stderr)
        return 2
    roles = sorted(result.specialists)
    if args.json:
        print(json.dumps({"tier": result.tier, "specialists": roles, "files": result.files}))
        return 0
    for path, tier in sorted(result.files.items()):
        print(f"  {tier} {path}")
    print(f"specialists: {', '.join(roles) or 'none'}")
    print(f"review-tier: {result.tier}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
