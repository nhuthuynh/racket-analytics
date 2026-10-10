#!/usr/bin/env bash
# CI-OBJSTORE-STALL experiment (temporary; removed before merge). Per iteration and per store
# variant: a fresh Compose object store, the 4x3 clip writes through each client path, one JSON
# row per write in OUT, and the store namespace's TCP counters (/proc/PID/net/netstat) before
# and after.   objstore_stall_loop.sh OUT ITERATIONS "VARIANTS" PATH...
#   VARIANT: base | rmem | mtu (compose.<variant>.yaml next to this script)
#   PATH: proxy (127.0.0.1 published port) | direct (the container's bridge IP)
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
out=$1 n=$2 variants=$3; shift 3
set -a; . infra/env.example; S3_HOST_PORT=${STALL_S3_PORT:-$S3_HOST_PORT}; set +a
counters() { sudo cat "/proc/$1/net/netstat" "/proc/$1/net/snmp" 2>/dev/null | python3 "$here/objstore_stall_counters.py"; }
for i in $(seq 1 "$n"); do
  for v in $variants; do
    files=(-f infra/compose.yaml); [[ $v != base ]] && files+=(-f "$here/compose.$v.yaml")
    compose=(docker compose -p "stall${STALL_PROJECT:-}" "${files[@]}" --env-file infra/env.example)
    "${compose[@]}" up -d --wait objectstore >/dev/null 2>&1 || { echo "iteration $i $v: store did not start"; "${compose[@]}" logs objectstore | tail -5; continue; }
    "${compose[@]}" run --rm objectstore-init >/dev/null 2>&1 || echo "iteration $i $v: init failed"
    cid=$("${compose[@]}" ps -q objectstore)
    pid=$(docker inspect -f '{{.State.Pid}}' "$cid")
    ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' "$cid" | awk '{print $1}')
    echo "$pid" >"${out%.jsonl}.storepid"
    before=$(counters "$pid")
    for p in "$@"; do
      case $p in
        proxy) ep="http://127.0.0.1:${S3_HOST_PORT}" ;;
        direct) ep="http://${ip}:8333" ;;
      esac
      (cd backend && PYTHONPATH=. S3_ENDPOINT_URL=$ep timeout 300 uv run --no-sync python \
        ../scripts/ci/experiments/objstore_stall_probe.py "$v/$p" "$ep") \
        | sed "s/^{/{\"it\": $i, /" >>"$out"
    done
    after=$(counters "$pid")
    echo "{\"it\": $i, \"counters\": \"$v\", \"before\": $before, \"after\": $after}" >>"$out"
    echo "iteration $i $v: lo $(docker exec "$cid" cat /sys/class/net/lo/mtu) rmem $(sudo nsenter -t "$pid" -n cat /proc/sys/net/ipv4/tcp_rmem | tr '\t' ' '); $(grep -c "\"it\": $i, \"label\": \"$v/" "$out") writes"
    "${compose[@]}" logs --no-color objectstore >"${out%.jsonl}.store-$v-$i.log" 2>&1
    "${compose[@]}" down -v >/dev/null 2>&1
  done
done
