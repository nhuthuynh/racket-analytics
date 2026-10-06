#!/usr/bin/env bash
# One door for E2E evidence runs (ADR 0033 rule 3; sprint-02 rows C-05, C-15, C-23).
#
#   bash scripts/ci/evidence.sh e2e RUN_DIR [playwright test args...]
#       Disk precheck (C-23), then Playwright from web/ with --output RUN_DIR/pw-out, holding
#       the evidence lock.
#   bash scripts/ci/evidence.sh up PROJECT ENV_FILE
#       Build floor check (RA_UP_MIN_FREE_GB, default 16), then under the lock
#       `docker compose -p PROJECT -f infra/compose.yaml --env-file ENV_FILE up -d --build --wait`.
#   bash scripts/ci/evidence.sh down PROJECT ENV_FILE
#       Under the lock `... down -v --rmi local --remove-orphans` (C-15), `df -h /` before and
#       after, and rc 5 if any PROJECT-* image is still there.
#
# PROJECT must be racket-<lower-case id> and never racket-analytics (the developer stack).
#
# Why: concurrent agents shared web/test-results and produced false reds (QA-R3-E2E-02). Every
# evidence run therefore writes its own output directory and takes one shared lock,
# .local/evidence-e2e.lock, for as long as Playwright runs.
#
# Exit codes: the command's own rc; 2 usage; 3 below the disk floor (scripts/disk-precheck.sh,
# RA_MIN_FREE_GB, default 10 GB: evidence from a full disk is not valid); 4 lock not acquired
# within RA_EVIDENCE_LOCK_WAIT_S; 5 an image of the project survived `down`.
# Overrides (tests): RA_EVIDENCE_PLAYWRIGHT (default "pnpm exec playwright test"),
# RA_EVIDENCE_DOCKER (default "docker"), RA_EVIDENCE_LOCK, RA_EVIDENCE_LOCK_WAIT_S (default 3600).
# RA_EVIDENCE_COMPOSE_EXTRA: space-separated extra compose files after infra/compose.yaml (e.g.
# a sandbox-only build-CA override; never committed).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOCK="${RA_EVIDENCE_LOCK:-$REPO_ROOT/.local/evidence-e2e.lock}"
LOCK_WAIT_S="${RA_EVIDENCE_LOCK_WAIT_S:-3600}"
RA_MIN_FREE_GB="${RA_MIN_FREE_GB:-10}"
export RA_MIN_FREE_GB
# A fresh build of the app images plus volumes took about 6 GB (disk-and-prune.md, 2026-10-05).
UP_MIN_FREE_GB="${RA_UP_MIN_FREE_GB:-16}"
DOCKER="${RA_EVIDENCE_DOCKER:-docker}"
COMPOSE_FILE="$REPO_ROOT/infra/compose.yaml"

usage() {
  cat >&2 <<'MSG'
usage: evidence.sh e2e RUN_DIR [playwright test args...]
       evidence.sh up PROJECT ENV_FILE
       evidence.sh down PROJECT ENV_FILE
MSG
  exit 2
}

disk_precheck() {
  # Prints the `df -h` line (the evidence); rc 3 below the floor (PD-R2R-10).
  bash "$REPO_ROOT/scripts/disk-precheck.sh" / || exit $?
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
  disk_precheck
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

stack_args() {
  # Validates PROJECT and ENV_FILE; sets PROJECT and ENV_FILE.
  [[ $# -eq 2 ]] || { echo "evidence: PROJECT and ENV_FILE are required" >&2; usage; }
  PROJECT="$1"
  ENV_FILE="$(abspath "$2")"
  if [[ ! "$PROJECT" =~ ^racket-[a-z0-9][a-z0-9-]*$ || "$PROJECT" == racket-analytics ]]; then
    echo "evidence: project '$PROJECT' is not an own evidence project (racket-<id>, not racket-analytics)" >&2
    exit 2
  fi
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "evidence: env file not found: $ENV_FILE" >&2
    exit 2
  fi
  COMPOSE_FILES=(-f "$COMPOSE_FILE")
  local extra
  read -r -a extra <<<"${RA_EVIDENCE_COMPOSE_EXTRA:-}"
  local f
  for f in "${extra[@]}"; do
    [[ -f "$f" ]] || { echo "evidence: extra compose file not found: $f" >&2; exit 2; }
    COMPOSE_FILES+=(-f "$f")
  done
}

compose() {
  "$DOCKER" compose -p "$PROJECT" "${COMPOSE_FILES[@]}" --env-file "$ENV_FILE" "$@"
}

cmd_up() {
  stack_args "$@"
  RA_MIN_FREE_GB="$UP_MIN_FREE_GB" bash "$REPO_ROOT/scripts/disk-precheck.sh" / || exit $?
  take_lock
  compose up -d --build --wait
  # The run itself still needs the 10 GB floor once the images exist.
  disk_precheck
}

cmd_down() {
  stack_args "$@"
  take_lock
  df -h /
  compose down -v --rmi local --remove-orphans
  df -h /
  local left
  left="$("$DOCKER" image ls -q --filter "reference=${PROJECT}-*")"
  if [[ -n "$left" ]]; then
    echo "evidence down: images of $PROJECT are left: $left" >&2
    exit 5
  fi
  echo "evidence down: $PROJECT removed with its volumes and images" >&2
}

[[ $# -ge 1 ]] || usage
sub="$1"
shift
case "$sub" in
  e2e) cmd_e2e "$@" ;;
  up) cmd_up "$@" ;;
  down) cmd_down "$@" ;;
  *) usage ;;
esac
