#!/usr/bin/env bash
# Runner and object store telemetry for the integration job (CI-OBJSTORE-SLOW).
# Runs 37764445816 and 37961668800: minutes into the job the SeaweedFS store took the 1.72 MB clip
# at ~64 KiB/s (one 64 KiB window per ~1.01 s) while small writes stayed fast; locally neither
# CPU, memory or IO limits, docker-proxy, volume growth nor a full disk reproduce that rate
# (docs/sprints/03/decisions/CI-OBJSTORE-SLOW.md). This records what only the runner can show.
#
#   objectstore_telemetry.sh facts OUT            once: daemon, port path, conntrack, firewall, disk
#   objectstore_telemetry.sh sample OUT           append one sample: a timed clip write + counters
#   objectstore_telemetry.sh watch OUT [SECONDS]  sample every SECONDS (default 15) until killed
#
# Env: S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_REGION, S3_BUCKET_MEDIA;
# TELEMETRY_CLIP (default fixtures/clips/synthetic-60s/clip.mp4). Every probe is best effort: a
# missing tool or a refused write is written down, never fatal (exit 2 only on bad usage).
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
clip="${TELEMETRY_CLIP:-$here/../../fixtures/clips/synthetic-60s/clip.mp4}"
usage() { echo "usage: objectstore_telemetry.sh facts|sample|watch OUT [SECONDS]" >&2; exit 2; }

mode="${1:-}"
out="${2:-}"
[[ -n "$out" ]] || usage
case "$mode" in facts | sample | watch) ;; *) usage ;; esac
mkdir -p "$(dirname "$out")"

endpoint="${S3_ENDPOINT_URL:-http://127.0.0.1:8333}"
port="${endpoint##*:}"
port="${port%%/*}"
section() { printf '\n## %s\n' "$1"; }
try() { timeout 20 "$@" 2>&1 || echo "(unavailable: $*)"; }
as_root() { if [[ $(id -u) -eq 0 ]]; then try "$@"; else try sudo -n "$@"; fi; }
read_files() { for f in "$@"; do [[ -r "$f" ]] && echo "$f: $(tr '\n' ' ' <"$f")"; done; true; }

facts() {
  echo "# facts $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  section "kernel"
  try uname -a
  read_files /proc/sys/net/ipv4/tcp_congestion_control /proc/sys/net/ipv4/tcp_window_scaling \
    /proc/sys/net/ipv4/tcp_rmem /proc/sys/net/ipv4/tcp_wmem /proc/sys/net/core/default_qdisc
  section "memory"
  try free -m
  section "disk"
  try df -h / /var/lib/docker /mnt
  section "docker daemon"
  read_files /etc/docker/daemon.json
  try docker info --format 'server={{.ServerVersion}} driver={{.Driver}} cgroup={{.CgroupDriver}}/{{.CgroupVersion}} root={{.DockerRootDir}} logging={{.LoggingDriver}}'
  local ids
  mapfile -t ids < <(docker ps -q 2>/dev/null)
  [[ ${#ids[@]} -eq 0 ]] || try docker inspect --format \
    '{{.Name}} cgroup_parent={{.HostConfig.CgroupParent}} mem={{.HostConfig.Memory}} cpus={{.HostConfig.NanoCpus}}' "${ids[@]}"
  section "published port path"
  try docker ps --format '{{.Names}} {{.Ports}}'
  pgrep -a docker-proxy || echo "(no docker-proxy process)"
  read_files /proc/sys/net/ipv4/conf/all/route_localnet
  as_root iptables -t nat -S
  section "conntrack settings"
  read_files /proc/sys/net/netfilter/nf_conntrack_tcp_be_liberal /proc/sys/net/netfilter/nf_conntrack_tcp_loose \
    /proc/sys/net/netfilter/nf_conntrack_max /proc/sys/net/netfilter/nf_conntrack_count \
    /proc/sys/net/netfilter/nf_conntrack_tcp_timeout_established
  section "invalid-packet rules"
  as_root sh -c 'iptables-save | grep -i invalid || echo "(no iptables INVALID rule)"'
  as_root sh -c 'nft list ruleset | grep -i invalid || echo "(no nftables invalid rule)"'
  section "cgroup"
  read_files /proc/self/cgroup /sys/fs/cgroup/actions_job/memory.max /sys/fs/cgroup/actions_job/io.max \
    /sys/fs/cgroup/actions_job/cpu.max
}

tcp_counters() {
  # /proc/net/snmp and /proc/net/netstat hold a header line and a value line per protocol.
  for f in /proc/net/snmp /proc/net/netstat; do
    [[ -r "$f" ]] || continue
    awk '$1=="Tcp:"||$1=="TcpExt:"{ if (k[$1]=="") {k[$1]=$0} else {
      n=split(k[$1],h," "); split($0,v," "); line=$1; for(i=2;i<=n;i++) line=line" "h[i]"="v[i]; print line } }' "$f"
  done
}

sample() {
  echo "# sample $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  section "write"
  local key bytes res code secs
  key="test-own/telemetry/$(date -u +%Y%m%dT%H%M%S)-$$-$RANDOM"
  bytes=$(stat -c %s "$clip" 2>/dev/null || echo 0)
  res=$(curl -sS -o /dev/null -w '%{http_code} %{time_total}' --max-time 60 \
    --aws-sigv4 "aws:amz:${S3_REGION:-us-east-1}:s3" --user "${S3_ACCESS_KEY_ID:-}:${S3_SECRET_ACCESS_KEY:-}" \
    -T "$clip" "$endpoint/${S3_BUCKET_MEDIA:-}/$key" 2>/dev/null)
  code=${res%% *}
  secs=${res##* }
  [[ -n "$code" && "$code" != "$res" ]] || { code=000; secs=0; }
  awk -v b="$bytes" -v s="$secs" -v c="$code" \
    'BEGIN { printf "write bytes=%d seconds=%.3f MBps=%.2f http=%s\n", b, s, (s > 0 ? b / s / 1e6 : 0), c }'
  curl -sS -o /dev/null --max-time 10 -X DELETE --aws-sigv4 "aws:amz:${S3_REGION:-us-east-1}:s3" \
    --user "${S3_ACCESS_KEY_ID:-}:${S3_SECRET_ACCESS_KEY:-}" "$endpoint/${S3_BUCKET_MEDIA:-}/$key" 2>/dev/null || true
  section "tcp counters"
  tcp_counters
  section "conntrack stats"
  read_files /proc/sys/net/netfilter/nf_conntrack_count /proc/net/stat/nf_conntrack
  [[ -r /proc/net/stat/nf_conntrack ]] || echo "(no /proc/net/stat/nf_conntrack)"
  section "store sockets"
  try ss -tinmo state established "( sport = :$port or dport = :$port or sport = :8333 or dport = :8333 )"
  section "pressure"
  read_files /proc/pressure/cpu /proc/pressure/io /proc/pressure/memory
  grep -E '^(Dirty|Writeback|MemAvailable):' /proc/meminfo 2>/dev/null || true
  section "store container"
  local store
  store=$(docker ps --filter name=objectstore --format '{{.Names}}' 2>/dev/null | head -1)
  if [[ -n "$store" ]]; then
    try docker stats --no-stream --format '{{.Name}} cpu={{.CPUPerc}} mem={{.MemUsage}} net={{.NetIO}} block={{.BlockIO}}' "$store"
    try docker exec "$store" du -sm /data
  else
    echo "(no objectstore container)"
  fi
  try df -h /
}

case "$mode" in
  facts) facts >"$out" ;;
  sample) sample >>"$out" ;;
  watch)
    interval="${3:-15}"
    [[ "$interval" =~ ^[1-9][0-9]*$ ]] || usage
    while true; do
      sample >>"$out"
      sleep "$interval"
    done
    ;;
esac
exit 0
