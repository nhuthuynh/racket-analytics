#!/usr/bin/env bash
# CI-OBJSTORE-STALL experiment (temporary; removed before merge). A fresh Compose object store
# per iteration; the 4x3 clip writes through each path; one JSON row per write in OUT.
#   objstore_stall_loop.sh OUT ITERATIONS PATH...   PATH: proxy (127.0.0.1 published port) |
#   direct (the container's bridge IP, no docker-proxy)
set -uo pipefail
out=$1 n=$2; shift 2
COMPOSE=${COMPOSE:-docker compose -f infra/compose.yaml --env-file infra/env.example}
set -a; . infra/env.example; set +a
for i in $(seq 1 "$n"); do
  $COMPOSE up -d --wait objectstore >/dev/null 2>&1 || { echo "iteration $i: store did not start"; continue; }
  $COMPOSE run --rm objectstore-init >/dev/null 2>&1 || echo "iteration $i: init failed"
  cid=$($COMPOSE ps -q objectstore)
  ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' "$cid" | awk '{print $1}')
  paths=("$@"); (( i % 2 == 0 )) && paths=($(printf '%s\n' "$@" | tac))
  for p in "${paths[@]}"; do
    case $p in
      proxy | dnat) ep="http://127.0.0.1:${S3_HOST_PORT}" ;;
      direct) ep="http://${ip}:8333" ;;
    esac
    (cd backend && PYTHONPATH=. S3_ENDPOINT_URL=$ep timeout 300 uv run --no-sync python \
      ../scripts/ci/experiments/objstore_stall_probe.py "$p" "$ep") \
      | sed "s/^{/{\"it\": $i, /" >>"$out"
  done
  echo "iteration $i: $(pgrep -c docker-proxy || true) docker-proxy processes; $(grep -c "\"it\": $i," "$out") writes"
  $COMPOSE logs --no-color objectstore >"${out%.jsonl}.store-$i.log" 2>&1
  $COMPOSE down -v >/dev/null 2>&1
done
