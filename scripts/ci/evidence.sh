#!/usr/bin/env bash
# One door for E2E evidence runs (ADR 0033 rule 3; sprint-02 rows C-05, C-15, C-23).
#
#   bash scripts/ci/evidence.sh e2e RUN_DIR [playwright test args...]
#       Playwright from web/ with --output RUN_DIR/pw-out, holding the evidence lock.
#
# Why: concurrent agents shared web/test-results and produced false reds (QA-R3-E2E-02). Every
# evidence run therefore writes its own output directory and takes one shared lock,
# .local/evidence-e2e.lock, for as long as Playwright runs.
#
# Exit codes: the command's own rc; 2 usage; 4 lock not acquired within RA_EVIDENCE_LOCK_WAIT_S.
# Overrides (tests): RA_EVIDENCE_PLAYWRIGHT (default "pnpm exec playwright test"),
# RA_EVIDENCE_LOCK, RA_EVIDENCE_LOCK_WAIT_S (default 3600).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOCK="${RA_EVIDENCE_LOCK:-$REPO_ROOT/.local/evidence-e2e.lock}"
LOCK_WAIT_S="${RA_EVIDENCE_LOCK_WAIT_S:-3600}"

usage() {
  cat >&2 <<'MSG'
usage: evidence.sh e2e RUN_DIR [playwright test args...]
MSG
  exit 2
}

take_lock() {
  mkdir -p "$(dirname "$LOCK")"
  exec 9>>"$LOCK"
  if ! flock -w "$LOCK_WAIT_S" 9; then
    echo "evidence: could not take the lock $LOCK within ${LOCK_WAIT_S} s (another evidence run holds it)" >&2
    exit 4
  fi
}

abspath() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s/%s\n' "$PWD" "$1" ;;
  esac
}

cmd_e2e() {
  [[ $# -ge 1 && -n "$1" ]] || { echo "evidence e2e: RUN_DIR is required" >&2; usage; }
  local run_dir
  run_dir="$(abspath "$1")"
  shift
  local arg
  for arg in "$@"; do
    if [[ "$arg" == "--output" || "$arg" == --output=* ]]; then
      echo "evidence e2e: do not pass --output; it is always RUN_DIR/pw-out" >&2
      exit 2
    fi
  done
  mkdir -p "$run_dir"
  take_lock
  local -a pw
  read -r -a pw <<<"${RA_EVIDENCE_PLAYWRIGHT:-pnpm exec playwright test}"
  cd "$REPO_ROOT/web"
  set +e
  "${pw[@]}" --output "$run_dir/pw-out" "$@"
  local rc=$?
  set -e
  echo "evidence e2e: rc=$rc output=$run_dir/pw-out" >&2
  exit "$rc"
}

[[ $# -ge 1 ]] || usage
sub="$1"
shift
case "$sub" in
  e2e) cmd_e2e "$@" ;;
  *) usage ;;
esac
