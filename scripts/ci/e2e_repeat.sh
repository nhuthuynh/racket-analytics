#!/usr/bin/env bash
# E2E repeat run for flake triage (NFR-074; CI-FLAKE-RESUMABLE), from web/ against a running stack.
# Env: SPEC (under web/e2e), GREP (as typed; empty = whole spec), REPEAT (1-99), PROJECT
# (chromium|webkit), REPORT_DIR, EVENT (pull_request runs the two resume titles; PE-PR10-M1).
# Exit: 2 refused input; 1 a flaky test (flaky_report.py); else Playwright's code, so a test that
# fails every time (broken, not flaky) fails too. No retries (playwright.config.ts retries: 0).
set -euo pipefail

spec="${SPEC:-e2e/sprint-01/resumable-upload.spec.ts}"
grep="${GREP:-}"
[[ "${EVENT:-}" != pull_request ]] || grep='Return after closing the tab|A different file is chosen to resume'
repeat="${REPEAT:-20}"
project="${PROJECT:-chromium}"
out="${REPORT_DIR:-../reports}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
refuse() { echo "e2e-repeat: $1" >&2; exit 2; }

[[ "$spec" =~ ^e2e/[A-Za-z0-9_./-]+\.spec\.ts$ && "$spec" != *..* ]] ||
  refuse "spec must be a .spec.ts path under web/e2e, got '$spec'"
[[ "$repeat" =~ ^[1-9][0-9]?$ ]] || refuse "repeat must be a number from 1 to 99, got '$repeat'"
[[ "$project" == chromium || "$project" == webkit ]] || refuse "project must be chromium or webkit, got '$project'"

mkdir -p "$out"
junit="$out/e2e-repeat.xml"
report="$out/e2e-repeat-flaky.md"
args=("$spec" "--repeat-each=$repeat" --workers=1 "--reporter=line,junit")
if [[ -n "$grep" ]]; then args+=(--grep "$grep"); fi

rc=0
PW_PROJECTS="$project" PLAYWRIGHT_JUNIT_OUTPUT_NAME="$junit" pnpm exec playwright test "${args[@]}" || rc=$?
[[ -s "$junit" ]] || { echo "e2e-repeat: Playwright wrote no JUnit file (exit $rc)" >&2; exit 1; }
flaky_rc=0
python3 "$here/flaky_report.py" --fail-on-flaky --out "$report" "$junit" || flaky_rc=$?
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then cat "$report" >> "$GITHUB_STEP_SUMMARY"; fi
if [[ "$flaky_rc" -ne 0 ]]; then exit "$flaky_rc"; fi
exit "$rc"
