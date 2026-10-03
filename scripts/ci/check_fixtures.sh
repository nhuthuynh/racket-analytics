#!/usr/bin/env bash
# Fixture and gold-set integrity gate (ST-011, FR-151, NFR-078). Runs QA's
# `racket-manifest-check` on every set under fixtures/ that has a manifest.json, passing the
# merge-base manifest when one exists so a hash change without a version bump fails.
# Usage: scripts/ci/check_fixtures.sh [BASE_REF]   (BASE_REF default: none = no base check)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE_REF="${1:-}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mapfile -t manifests < <(cd "$ROOT" && find fixtures -name manifest.json -type f | sort)
if [[ ${#manifests[@]} -eq 0 ]]; then
  echo "fixtures: no manifest.json found under fixtures/; failing closed"
  exit 2
fi

status=0
for m in "${manifests[@]}"; do
  dir="$(dirname "$m")"
  args=("$ROOT/$dir")
  if [[ -n "$BASE_REF" ]] && git -C "$ROOT" cat-file -e "$BASE_REF:$m" 2>/dev/null; then
    base="$TMP/$(echo "$m" | tr '/' '_')"
    git -C "$ROOT" show "$BASE_REF:$m" > "$base"
    args+=(--base-manifest "$base")
  fi
  echo "== $dir"
  (cd "$ROOT/backend" && uv run --quiet racket-manifest-check "${args[@]}") || status=1
done
exit "$status"
