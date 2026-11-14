#!/usr/bin/env bash
# pr-check (CI-FIX-PR-CHECK): CI's PR policy, doc, Ruff and unit gates on this branch, before a push.
# The commands are ci.yml's own (pr-policy, doc-check, python-lint; scripts/test-unit.sh for the
# unit suites), against origin/main after `git fetch origin main`; infra/tests/test_pr_check.py
# fails when ci.yml changes a command this script does not. Every check runs even after one fails;
# one PASS/FAIL/SKIP line per check names the CI job and step; exit 1 if any failed.
# With an open PR for the branch, PR_NUMBER, PR_TITLE, GITHUB_REPOSITORY and GITHUB_TOKEN are
# exported, so the PR's current labels (size-waiver, qa-approved-test-change) count as in CI and
# the cost-table step runs on its title. Agents run it before every push (docs/process/ci-cd.md);
# .githooks/pre-push runs it for s<nn>/* branches (`make hooks`).
# Usage: scripts/pr-check.sh [--fast] [--branch NAME]
#   --fast         skip the unit suites (nothing else can be skipped)
#   --branch NAME  the remote branch name used to find the open PR (default: the current branch)
# shellcheck disable=SC2016 # each snippet expands in its own step shell, as in ci.yml
set -uo pipefail

usage() { echo "usage: scripts/pr-check.sh [--fast] [--branch NAME]"; }

fast=0
branch=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --fast) fast=1 ;;
    --branch) branch="${2:-}"; shift ;;
    --branch=*) branch="${1#--branch=}" ;;
    -h | --help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
  shift
done

root="$(git rev-parse --show-toplevel)" || exit 2
cd "$root" || exit 2
[[ -n "$branch" ]] || branch="$(git symbolic-ref --short -q HEAD || true)"

results=()
failed=0
# check LABEL SNIPPET: runs SNIPPET as a CI step does (bash -e -o pipefail), records the verdict.
check() {
  echo
  echo "== $1"
  if bash -e -o pipefail -c "$2"; then
    results+=("PASS  $1")
  else
    results+=("FAIL  $1")
    failed=$((failed + 1))
  fi
}
skip() {
  echo
  echo "== $1: skipped, $2"
  results+=("SKIP  $1")
}

# Never a stale value from the shell: only an open PR found below sets these.
unset PR_NUMBER PR_TITLE PR_LABELS
export BASE_REF="main" # CI's github.base_ref of a PR into main

check "base / git fetch origin main" 'git fetch origin main'

# The open PR for the branch, as GitHub lists it (REST, like every script here).
pr_note="no open pull request for ${branch:-a detached HEAD}"
if [[ -n "$branch" ]]; then
  repo="${GITHUB_REPOSITORY:-$(git remote get-url origin 2>/dev/null \
    | sed -E 's#\.git$##; s#^.*[:/]([^/:]+/[^/]+)$#\1#')}"
  if pulls="$(gh api "repos/$repo/pulls?head=${repo%%/*}:$branch&state=open" 2>&1)"; then
    mapfile -t pr < <(printf '%s' "$pulls" | python3 -c '
import json, sys
pulls = json.load(sys.stdin)
if pulls:
    print(pulls[0]["number"])
    print(" ".join(str(pulls[0]["title"]).split()))
')
    if [[ ${#pr[@]} -eq 2 ]]; then
      export PR_NUMBER="${pr[0]}" PR_TITLE="${pr[1]}" GITHUB_REPOSITORY="$repo"
      GITHUB_TOKEN="${GITHUB_TOKEN:-$(gh auth token 2>/dev/null || echo x)}"
      export GITHUB_TOKEN
      pr_note=""
      echo "pr-check: open PR #$PR_NUMBER on $repo: labels and title are read as in CI"
    fi
  else
    pr_note="the open pull request lookup failed (${pulls//$'\n'/ })"
  fi
fi
[[ -z "$pr_note" ]] || echo "pr-check: $pr_note; labels such as size-waiver do not apply"

# ---- pr-policy: PR policy (test immutability, size), ci.yml's run lines verbatim
check "pr-policy / Test and gold immutability (EP/ENG-28, NFR-078)" \
  'python3 scripts/ci/check_test_immutability.py --base "origin/$BASE_REF" --head HEAD'
check "pr-policy / PR size (EP/ENG-04)" \
  'python3 scripts/ci/check_pr_size.py --base "origin/$BASE_REF" --head HEAD'
check "pr-policy / Red first (R3-IN-1, C4-RED)" \
  'python3 scripts/ci/check_red_first.py --base "origin/$BASE_REF" --head HEAD'
# Reads only the branch's diff, so it runs with or without an open PR.
check "pr-policy / Decisions findings joined to the ledger (PRC-4.1, PRC-4.2)" \
  'python3 scripts/measure/reconcile_due.py --pr --base "origin/$BASE_REF" --head HEAD'
if [[ -z "$pr_note" ]]; then
  check "pr-policy / Cost per PR table (PRC-11.3)" 'python3 scripts/ci/check_cost_table.py'
else
  skip "pr-policy / Cost per PR table (PRC-11.3)" "$pr_note (it needs the PR title; CI runs it)"
fi

# ---- doc-check: Doc checks (paths, citations, agent front matter, decider cells)
# CI diffs from the PR's base SHA; locally that is the fetched origin/main.
BASE_SHA="$(git rev-parse -q --verify origin/main || true)"
export BASE_SHA
check "doc-check / Doc checks (paths, citations, agent front matter, decider cells): check_docs.py" '
if [ -z "$BASE_SHA" ] || [ "$BASE_SHA" = "0000000000000000000000000000000000000000" ]; then
  BASE_SHA="$(git rev-parse HEAD^)"
fi
python3 scripts/ci/check_docs.py --base "$BASE_SHA" --head HEAD'
check "doc-check / Doc checks (paths, citations, agent front matter, decider cells): check_atomic_breakdown.py" \
  'python3 scripts/ci/check_atomic_breakdown.py'

# ---- python-lint: Python lint and format (Ruff), in backend/ (CI adds --output-format=github)
check "python-lint / uv run ruff check" 'cd backend && uv run ruff check .'
check "python-lint / uv run ruff format --check ." 'cd backend && uv run ruff format --check .'

# ---- python-unit (and web unit): the unit suites, as `make test-unit` and the Stop hook run them
if [[ $fast -eq 1 ]]; then
  skip "python-unit / Unit suites (scripts/test-unit.sh)" "--fast"
else
  check "python-unit / Unit suites (scripts/test-unit.sh)" 'scripts/test-unit.sh'
fi

echo
echo "== pr-check summary (base origin/main, branch ${branch:-detached} at $(git rev-parse --short HEAD))"
printf '%s\n' "${results[@]}"
if [[ $failed -gt 0 ]]; then
  echo "pr-check: $failed check(s) failed; CI fails the same steps. Fix them before pushing."
  exit 1
fi
echo "pr-check: every check passed (integration, E2E, types and web checks still run in CI)"
