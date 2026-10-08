#!/usr/bin/env bash
# E2E repeat run for flake triage (NFR-074; CI-FLAKE-RESUMABLE). Run from web/ against a running
# stack. Inputs come from the environment (never interpolated by the workflow into this line):
#   SPEC     a spec under web/e2e (default e2e/sprint-01/resumable-upload.spec.ts)
#   GREP     optional title filter (Playwright --grep)
#   REPEAT   1-99 (default 20)
#   PROJECT  chromium | webkit (default chromium)
#   REPORT_DIR  where e2e-repeat.xml and e2e-repeat-flaky.md go (default ../reports)
# Exit: Playwright's exit code (a test that fails every time is broken, not flaky), 1 when the
# flaky report finds a test that both passed and failed, 2 on a refused input. No retries
# (playwright.config.ts retries: 0).
set -euo pipefail

spec="${SPEC:-e2e/sprint-01/resumable-upload.spec.ts}"
grep="${GREP:-}"
repeat="${REPEAT:-20}"
project="${PROJECT:-chromium}"
out="${REPORT_DIR:-../reports}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! "$spec" =~ ^e2e/[A-Za-z0-9_./-]+\.spec\.ts$ || "$spec" == *..* ]]; then
  echo "e2e-repeat: spec must be a .spec.ts path under web/e2e, got '$spec'" >&2
  exit 2
fi
if [[ ! "$repeat" =~ ^[1-9][0-9]?$ ]]; then
  echo "e2e-repeat: repeat must be a number from 1 to 99, got '$repeat'" >&2
  exit 2
fi
if [[ "$project" != chromium && "$project" != webkit ]]; then
  echo "e2e-repeat: project must be chromium or webkit, got '$project'" >&2
  exit 2
fi

mkdir -p "$out"
junit="$out/e2e-repeat.xml"
report="$out/e2e-repeat-flaky.md"
args=("$spec" "--repeat-each=$repeat" --workers=1 "--reporter=line,junit")
if [[ -n "$grep" ]]; then args+=(--grep "$grep"); fi

set +e
PW_PROJECTS="$project" PLAYWRIGHT_JUNIT_OUTPUT_NAME="$junit" pnpm exec playwright test "${args[@]}"
rc=$?
set -e

if [[ ! -s "$junit" ]]; then
  echo "e2e-repeat: Playwright wrote no JUnit file (exit $rc)" >&2
  exit 1
fi
flaky_rc=0
python3 "$here/flaky_report.py" --fail-on-flaky --out "$report" "$junit" || flaky_rc=$?
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then cat "$report" >> "$GITHUB_STEP_SUMMARY"; fi
if [[ "$flaky_rc" -ne 0 ]]; then exit "$flaky_rc"; fi
exit "$rc"
