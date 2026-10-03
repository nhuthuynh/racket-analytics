#!/usr/bin/env bash
# Unit suites only (ST-003). Single entry point for the Stop hook, `make test-unit` and humans.
# Unit = no I/O, sleeps or network (EP/ENG-17). Excludes `slow` and QA's red-first
# `red_until` tests (ST-012), which are expected to fail until their story lands.
# Contract with other lanes:
#   backend: pytest marker `unit` (backend/pyproject.toml, QA-owned)
#   web:     package.json script `test:unit` (Vitest, FE-owned)
set -euo pipefail

ROOT="${RA_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
status=0
ran=0

if [[ -f "$ROOT/backend/pyproject.toml" ]]; then
  ran=1
  echo "== backend unit suite"
  rc=0
  (cd "$ROOT/backend" && uv run --quiet pytest -q -p no:cacheprovider \
      -m "unit and not slow and not red_until") || rc=$?
  if [[ $rc -eq 5 ]]; then
    echo "== backend: no unit tests collected yet"
  elif [[ $rc -ne 0 ]]; then
    status=1
  fi
else
  echo "== backend: no backend/pyproject.toml yet; skipped"
fi

if [[ -f "$ROOT/web/package.json" ]] && grep -q '"test:unit"' "$ROOT/web/package.json"; then
  if [[ -d "$ROOT/web/node_modules" ]]; then
    ran=1
    echo "== web unit suite"
    pnpm --dir "$ROOT/web" run --silent test:unit || status=1
  else
    echo "== web: node_modules missing (run 'pnpm --dir web install'); skipped"
  fi
else
  echo "== web: no test:unit script yet; skipped"
fi

if [[ $ran -eq 0 ]]; then
  echo "== no unit suites found; skipped"
fi
exit "$status"
