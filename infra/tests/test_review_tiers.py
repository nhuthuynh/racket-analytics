"""CI-TIERS-a unit tests for scripts/ci/review_tiers.py (PRC-2.1-2.3; ADR 0056; sprint-05.md §3.7).

The classifier maps a PR's changed files to a review tier (0 docs, 1 code, 2 security / personal
data / schema / API contract / merge gate) and to the specialist roles it flags. The rules are
data; resolution has no rule order: a file gets the highest tier of every rule it matches, the
PR the highest over its files, and an unmatched path is tier 2 (fail closed). An executable file
is at least tier 1 wherever it lives. Pure functions: no network, no disk, except the glob
liveness test, which reads `git ls-files` of this checkout. Negative cases first."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from types import ModuleType

import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR

pytestmark = pytest.mark.unit

SCRIPT = SCRIPTS_DIR / "ci" / "review_tiers.py"
MERGE_READY = SCRIPTS_DIR / "ci" / "merge_ready.py"


def _load(name: str, path: object) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)  # type: ignore[arg-type]
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rt() -> ModuleType:
    return _load("review_tiers", SCRIPT)


def tier(rt: ModuleType, *paths: str, **flags: bool) -> int:
    return rt.classify([rt.ChangedFile(p, **flags) for p in paths]).tier


# ------------------------------------------------------------------ executable floor (PRC-2.2)
@pytest.mark.parametrize(
    "path",
    [
        "docs/security/tools/check_threat_notes.py",
        "docs/security/tools/asvs_status.py",
        "docs/design/tools/check_flows.py",
        "docs/domain/tools/metric_example.py",
        "docs/sprints/05/close-checks/retro05_check.py",
        "docs/sprints/05/close-checks/retro05_check",
        "docs/notes/run.sh",
        "docs/notes/page.tsx",
        "docs/notes/query.sql",
        "docs/notes/Makefile",
        "docs/notes/Dockerfile.dev",
    ],
)
def test_an_executable_file_under_docs_is_at_least_tier_1(rt: ModuleType, path: str) -> None:
    assert tier(rt, path) >= 1


def test_an_extensionless_file_with_a_shebang_under_docs_is_tier_1(rt: ModuleType) -> None:
    assert tier(rt, "docs/tools/run-check", shebang=True) == 1


def test_a_markdown_file_with_the_executable_bit_is_tier_1(rt: ModuleType) -> None:
    assert tier(rt, "docs/x.md", executable=True) == 1


def test_a_workflow_file_is_never_below_tier_1(rt: ModuleType) -> None:
    assert tier(rt, ".github/workflows/notes.md") >= 1


# ------------------------------------------------- tier 2 and fail closed (PRC-2.1, 2.3)
@pytest.mark.parametrize(
    "path",
    [
        "docs/architecture/api-matches.md",
        "backend/src/racket/migrations/versions/0001_identity_and_matches.py",
        "backend/src/racket/migrations/env.py",
        "docs/sprints/05/ticket-owners.json",
        "scripts/ci/merge_ready.py",
        "scripts/ci/review_tiers.py",
        ".github/workflows/ci.yml",
        "backend/src/racket/video_ingest/domain/media_url.py",
        "backend/src/racket/platform/storage.py",
        "backend/src/racket/platform/logs.py",
        "backend/src/racket/platform/settings.py",
        "backend/src/racket/platform/ratelimit.py",
        "backend/src/racket/platform/purge.py",
        "backend/src/racket/platform/fault_injection.py",
        "backend/src/racket/players/service.py",
        "web/src/lib/auth/sign-in.ts",
        "web/src/lib/media/playback.ts",
        "web/src/lib/upload/transfer.ts",
        "web/src/components/settings/PrivacySettings.tsx",
        "web/src/lib/identity/age.ts",
        ".gitleaksignore",
        "infra/env.example",
        ".claude/settings.json",
    ],
)
def test_a_tier_2_path_is_tier_2(rt: ModuleType, path: str) -> None:
    assert tier(rt, path) == 2


@pytest.mark.parametrize("path", ["docs/unknown/thing.bin", "docs/diagram.png", "LICENSE", "x/y"])
def test_a_path_no_rule_matches_is_tier_2(rt: ModuleType, path: str) -> None:
    assert tier(rt, path) == 2


def test_the_highest_matching_rule_wins_over_the_tier_0_markdown_rule(rt: ModuleType) -> None:
    globs = [r.glob for r in rt.RULES if rt.glob_match(r.glob, "docs/architecture/api-x.md")]
    assert len(globs) >= 2, globs  # matched by the tier 0 docs rule and the tier 2 API rule
    assert tier(rt, "docs/architecture/api-x.md") == 2


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (("README.md", "docs/x.md", "docs/design/tools/check_flows.py"), 1),
        (("docs/x.md", "docs/architecture/api-x.md"), 2),
        (("docs/x.md", "docs/unknown/thing.bin"), 2),
        (("docs/x.md", "backend/src/racket/analytics/service.py"), 1),
        (("README.md", "docs/x.md", "docs/sprints/05/status.json"), 0),
    ],
)
def test_the_pr_gets_the_highest_tier_over_its_files(
    rt: ModuleType, paths: tuple[str, ...], expected: int
) -> None:
    assert tier(rt, *paths) == expected


def test_an_empty_change_set_fails_closed_to_tier_2(rt: ModuleType) -> None:
    assert rt.classify([]).tier == 2


# ------------------------------------------------------------------ tier 0 (PRC-2.2)
@pytest.mark.parametrize(
    "path",
    [
        "docs/sprints/05/status.json",
        "docs/sprints/sprint-05.md",
        "docs/x.md",
        "README.md",
        ".claude/agents/sre-devops-engineer.md",
    ],
)
def test_docs_and_process_text_alone_is_tier_0(rt: ModuleType, path: str) -> None:
    assert tier(rt, path) == 0


def test_a_nested_readme_outside_docs_is_not_tier_0(rt: ModuleType) -> None:
    assert tier(rt, "web/README.md") >= 1


def test_a_changed_tools_line_in_a_role_file_is_tier_2(rt: ModuleType) -> None:
    assert tier(rt, ".claude/agents/sre-devops-engineer.md", tools_line_changed=True) == 2


# ------------------------------------------------------------------ the tools: diff rule
BODY_ONLY = """\
--- a/.claude/agents/sre-devops-engineer.md
+++ b/.claude/agents/sre-devops-engineer.md
@@ -10,3 +10,3 @@
 <mission>
-Make shipping safe.
+Make shipping safe, fast and observable.
 </mission>
"""
TOOLS = """\
--- a/.claude/agents/sre-devops-engineer.md
+++ b/.claude/agents/sre-devops-engineer.md
@@ -3,3 +3,3 @@
 description: SRE
-tools: Read, Grep, Glob, Write, Edit, Bash
+tools: Read, Grep, Glob, Write, Edit, Bash, mcp__github__merge_pull_request
 model: sonnet
"""


def test_a_body_only_patch_does_not_change_the_tools_line(rt: ModuleType) -> None:
    assert rt.tools_line_changed(BODY_ONLY) is False


def test_a_patch_that_edits_the_tools_line_changes_it(rt: ModuleType) -> None:
    assert rt.tools_line_changed(TOOLS) is True


def test_an_added_tools_line_changes_it(rt: ModuleType) -> None:
    assert rt.tools_line_changed("@@ -2,0 +3 @@\n+tools: Bash\n") is True


def test_a_missing_patch_fails_closed(rt: ModuleType) -> None:
    assert rt.tools_line_changed(None) is True


# ------------------------------------------------------------------ specialists
@pytest.mark.parametrize(
    ("path", "role"),
    [
        ("web/src/components/stats/messages.ts", "principal-designer"),
        ("web/src/app/plan/page.tsx", "principal-designer"),
        ("backend/src/racket/coaching/drills/rules.py", "pickleball-domain-coach"),
        ("content/drills/serve.yaml", "pickleball-domain-coach"),
        ("backend/src/racket/worker/stages.py", "senior-ml-cv-engineer"),
        ("backend/src/racket/dataset/labels.py", "senior-ml-cv-engineer"),
        ("backend/src/racket/coaching/evals/runner.py", "senior-ml-cv-engineer"),
        ("web/src/lib/security/csp.ts", "senior-frontend-engineer"),
        ("web/src/middleware.ts", "senior-frontend-engineer"),
    ],
)
def test_a_path_flags_its_specialist(rt: ModuleType, path: str, role: str) -> None:
    assert role in rt.classify([rt.ChangedFile(path)]).specialists


def test_a_docs_only_pr_flags_no_specialist(rt: ModuleType) -> None:
    assert rt.classify([rt.ChangedFile("docs/x.md")]).specialists == frozenset()


def test_every_flagged_role_is_a_role_file(rt: ModuleType) -> None:
    roles = {p.stem for p in (REPO_ROOT / ".claude" / "agents").glob("*.md")}
    flagged = {role for rule in rt.RULES for role in rule.roles}
    assert flagged
    assert flagged <= roles, flagged - roles


# ------------------------------------------------------------------ globs
@pytest.mark.parametrize(
    ("glob", "path", "hit"),
    [
        ("docs/**/*.md", "docs/x.md", True),
        ("docs/**/*.md", "docs/a/b/x.md", True),
        ("docs/**/*.md", "docsx/x.md", False),
        ("*.md", "README.md", True),
        ("*.md", "docs/x.md", False),
        ("docs/sprints/*/status.json", "docs/sprints/05/status.json", True),
        ("docs/sprints/*/status.json", "docs/sprints/05/a/status.json", False),
        ("backend/src/racket/platform/fault*", "backend/src/racket/platform/fault.py", True),
        ("backend/src/racket/platform/fault*", "backend/src/racket/platform/x/fault.py", False),
        ("backend/src/racket/migrations/**", "backend/src/racket/migrations/versions/1.py", True),
        ("backend/src/racket/migrations/**", "backend/src/racket/migrationsx/1.py", False),
        ("scripts/ci/merge_ready.py", "scripts/ci/merge_readyXpy", False),
    ],
)
def test_glob_match(rt: ModuleType, glob: str, path: str, hit: bool) -> None:
    assert rt.glob_match(glob, path) is hit


# ------------------------------------------------------------------ glob liveness (PRC-2.3)
def _tracked() -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [p for p in out.split("\0") if p]


def test_every_tier2_glob_matches_a_tracked_path(rt: ModuleType) -> None:
    assert rt.dead_tier2_globs(_tracked()) == []


def test_a_tier2_glob_matching_nothing_is_named(rt: ModuleType) -> None:
    rules = (*rt.RULES, rt.Rule("backend/migrations/**", 2))
    problems = rt.dead_tier2_globs(_tracked(), rules=rules)
    assert len(problems) == 1
    assert "backend/migrations/**" in problems[0]


def test_a_pending_glob_that_now_matches_fails(rt: ModuleType) -> None:
    pending = {"backend/src/racket/platform/storage*": "ST-075d"}
    problems = rt.dead_tier2_globs(_tracked(), pending=pending)
    assert len(problems) == 1
    assert "backend/src/racket/platform/storage*" in problems[0]


def test_a_pending_glob_without_its_creating_ticket_fails(rt: ModuleType) -> None:
    problems = rt.dead_tier2_globs(_tracked(), pending={"backend/src/racket/nothing/**": ""})
    assert len(problems) == 1


def test_the_fault_seam_is_pending_on_st_075d(rt: ModuleType) -> None:
    assert rt.PENDING_GLOBS.get("backend/src/racket/platform/fault*") == "ST-075d"


# ------------------------------------------------- merge_ready imports the classifier
def test_merge_ready_computes_the_tier_with_the_classifier(rt: ModuleType) -> None:
    mr = _load("merge_ready", MERGE_READY)
    got = mr.review_tier([rt.ChangedFile("docs/x.md"), rt.ChangedFile("scripts/ci/merge_ready.py")])
    assert got.tier == 2
