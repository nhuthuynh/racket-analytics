#!/usr/bin/env bash
# Disk floor before any evidence run (working-agreement 1a, ADR 0030 rule 3; QA-R2V-05, QA-R3-03).
#
#   bash scripts/disk-precheck.sh [PATH]      # default PATH=/, floor RA_MIN_FREE_GB (default 10)
#
# Prints the `df -h` line (the evidence) and exits 0 when at least RA_MIN_FREE_GB GB are free.
# Exit 3 below the floor: below ~10 GB SeaweedFS refuses writes ("No more free space left") and
# uploads, the live goal run and the object-store parity tests fail for a reason that is not the
# code. Exit 2 on a malformed floor or a missing path. Prune procedure: docs/ops/disk-and-prune.md.
set -euo pipefail

path="${1:-/}"
floor="${RA_MIN_FREE_GB:-10}"

if ! [[ "$floor" =~ ^[0-9]+$ ]]; then
  echo "disk-precheck: RA_MIN_FREE_GB must be a whole number of GB, got '$floor'" >&2
  exit 2
fi
if [[ ! -e "$path" ]]; then
  echo "disk-precheck: no such path: $path" >&2
  exit 2
fi

df -h "$path"
avail_kb="$(df -Pk "$path" | awk 'NR==2 {print $4}')"
avail_gb=$(( avail_kb / 1024 / 1024 ))

if (( avail_gb < floor )); then
  cat >&2 <<MSG
disk-precheck: only ${avail_gb} GB free on ${path}, need >= ${floor} GB.
Evidence from this run would not be valid. The SRE prunes first (docs/ops/disk-and-prune.md):
  docker builder prune -af; docker image prune -af; docker volume prune -f   # stale only
then re-run this check.
MSG
  exit 3
fi
echo "disk-precheck: ok, ${avail_gb} GB free on ${path} (floor ${floor} GB)"
