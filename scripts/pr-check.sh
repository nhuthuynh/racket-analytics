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
step_env=() # VAR=value pairs for the next check only (the PR's env reaches pr-policy steps only)
record() { # record STATUS LABEL
  results+=("$1  $2")
  [[ $1 != FAIL ]] || failed=$((failed + 1))
}
# check LABEL SNIPPET: runs SNIPPET as a CI step does (bash -e -o pipefail), records the verdict.
check() {
  echo
  echo "== $1"
  if env "${step_env[@]}" bash -e -o pipefail -c "$2"; then record PASS "$1"; else record FAIL "$1"; fi
}
skip() {
  echo
  echo "== $1: skipped, $2"
  record SKIP "$1"
}
finish() {
  echo
  echo "== pr-check summary (base origin/main, branch ${branch:-detached} at $(git rev-parse --short HEAD))"
  printf '%s\n' "${results[@]}"
  if [[ $failed -gt 0 ]]; then
    echo "pr-check: $failed check(s) failed; CI fails the same steps. Fix them before pushing."
    exit 1
  fi
  echo "pr-check: every check passed (integration, E2E, types and web checks still run in CI)"
  exit 0
}

# Never a stale value from the shell: only an open PR found below sets these, for pr-policy.
unset PR_NUMBER PR_TITLE PR_LABELS
export BASE_REF="main" # CI's github.base_ref of a PR into main

check "base / git fetch origin main" 'git fetch origin main'

# ---- Judge what CI judges. CI tests the PR merged with current main, so it runs main's gate
# scripts: a branch behind main would be judged here by its own older copies (review B2).
label="base / branch contains origin/main"
echo
echo "== $label"
if git merge-base --is-ancestor origin/main HEAD 2>/dev/null; then
  record PASS "$label"
else
  echo "HEAD does not contain origin/main: CI runs main's newer gate scripts on the merged PR."
  echo "Run: git merge origin/main (a merge; pushed history is never rebased), then pr-check again."
  record FAIL "$label"
fi
# Ruff, the unit suites and the doc checks read the files on disk; CI reads the commit (review B1).
label="tree / no uncommitted or untracked changes"
echo
echo "== $label"
dirty="$(git status --porcelain --untracked-files=all)"
if [[ -z "$dirty" ]]; then
  record PASS "$label"
else
  printf '%s\n' "$dirty"
  echo "These files differ from HEAD, so the checks would not judge what you push:"
  echo "commit or stash them (git stash -u), then run pr-check again."
  record FAIL "$label"
fi
if [[ $failed -gt 0 ]]; then
  echo
  echo "pr-check: stopped before CI's checks; their verdicts would not be the ones CI gives."
  finish
fi

# The open PR for the branch, as GitHub lists it (REST, like every script here); the branch
# name is a form field, so gh encodes it.
pr_env=()
pr_note="no open pull request for ${branch:-a detached HEAD}"
lookup_failed=0
if [[ -n "$branch" ]]; then
  repo="${GITHUB_REPOSITORY:-$(git remote get-url origin 2>/dev/null \
    | sed -E 's#\.git$##; s#^.*[:/]([^/:]+/[^/]+)$#\1#')}"
  if pulls="$(gh api -X GET "repos/$repo/pulls" -f "head=${repo%%/*}:$branch" -f state=open 2>&1)" \
    && mapfile -t pr < <(printf '%s' "$pulls" | python3 -c '
import json, sys
pulls = json.load(sys.stdin)
if pulls:
    print(pulls[0]["number"])
    print(" ".join(str(pulls[0]["title"]).split()))
'); then
    if [[ ${#pr[@]} -eq 2 ]]; then
      token="${GITHUB_TOKEN:-$(gh auth token 2>/dev/null || echo x)}"
      pr_env=("PR_NUMBER=${pr[0]}" "PR_TITLE=${pr[1]}" "GITHUB_REPOSITORY=$repo" "GITHUB_TOKEN=$token")
      pr_note=""
      echo "pr-check: open PR #${pr[0]} on $repo: labels and title are read as in CI"
    elif [[ ${#pr[@]} -ne 0 ]]; then
      lookup_failed=1
      pr_note="the open pull request lookup returned an unreadable answer"
    fi
  else
    lookup_failed=1
    pr_note="the open pull request lookup failed (${pulls//$'\n'/ })"
  fi
fi
[[ -z "$pr_note" ]] || echo "pr-check: $pr_note; labels such as size-waiver do not apply"

# ---- pr-policy: PR policy (test immutability, size), ci.yml's run lines verbatim
step_env=("${pr_env[@]}")
check "pr-policy / Test and gold immutability (EP/ENG-28, NFR-078)" \
  'python3 scripts/ci/check_test_immutability.py --base "origin/$BASE_REF" --head HEAD'
check "pr-policy / PR size (EP/ENG-04)" \
  'python3 scripts/ci/check_pr_size.py --base "origin/$BASE_REF" --head HEAD'
check "pr-policy / Red first (R3-IN-1, C4-RED)" \
  'python3 scripts/ci/check_red_first.py --base "origin/$BASE_REF" --head HEAD'
# Reads only the branch's diff, so it runs with or without an open PR.
check "pr-policy / Decisions findings joined to the ledger (PRC-4.1, PRC-4.2)" \
  'python3 scripts/measure/reconcile_due.py --pr --base "origin/$BASE_REF" --head HEAD'
label="pr-policy / Cost per PR table (PRC-11.3)"
if [[ -z "$pr_note" ]]; then
  check "$label" 'python3 scripts/ci/check_cost_table.py'
elif [[ $lookup_failed -eq 1 ]]; then
  echo
  echo "== $label"
  echo "FAIL: $pr_note; whether a PR is open is unknown, so this step cannot be judged"
  record FAIL "$label"
else
  skip "$label" "$pr_note (it needs the PR title; CI runs it)"
fi
step_env=()

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

# ---- python-unit (and web unit): the unit suites, as `make test-unit` and the Stop hook run them.
# scripts/test-unit.sh runs the web suite only when web/node_modules exists; otherwise the web
# line is SKIP, never a PASS it did not earn.
unit="python-unit / Unit suites (scripts/test-unit.sh)"
web="web-checks / Web unit suite (pnpm test:unit)"
if [[ $fast -eq 1 ]]; then
  skip "$unit" "--fast"
  skip "$web" "--fast"
else
  check "$unit" 'scripts/test-unit.sh'
  if [[ ! -f web/package.json ]] || ! grep -q '"test:unit"' web/package.json; then
    skip "$web" "no test:unit script in web/package.json"
  elif [[ ! -d web/node_modules ]]; then
    skip "$web" "web/node_modules is missing (pnpm --dir web install); CI runs it"
  else
    echo
    echo "== $web: ran inside scripts/test-unit.sh above"
    results+=("${results[-1]%%  *}  $web") # the unit step's verdict; counted once
  fi
fi

finish
