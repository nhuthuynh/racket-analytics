#!/usr/bin/env bash
# Local S3-compatible object store without Docker: SeaweedFS (ADR 0008 part C), ST-001.
#
#   eval "$(scripts/dev-objectstore.sh start)"   # exports S3_* variables
#   scripts/dev-objectstore.sh env | status | stop
#   scripts/dev-objectstore.sh ports N           # N distinct free ports (what start uses)
#
# Downloads a pinned SeaweedFS release (sha256-verified) into <repo>/.local/bin unless
# WEED_BIN or `weed` on PATH is available. Binds 127.0.0.1 only, on free ports, with
# random per-instance credentials, and creates the media bucket. `stop` deletes the data.
# A start that dies of a port collision ("address already in use") is retried on fresh ports
# up to 3 times; any other startup failure fails at once.
#
# Env: WEED_BIN, RA_DEV_STATE (default <repo>/.local), S3_BUCKET_MEDIA (default racket-media).
set -euo pipefail

WEED_VERSION="3.97"
# sha256 of linux_amd64.tar.gz for 3.97, recorded 2026-10-03 (docs/sprints/00/decision-log.md)
WEED_SHA256_LINUX_AMD64="a5b73384efb1b3848e8ba464420475b2e0c12c17c32d7939546cd496728849a7"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${RA_DEV_STATE:-$ROOT/.local}"
STATE_FILE="$STATE_DIR/objectstore.state"
CACHE_BIN="$ROOT/.local/bin"
BUCKET="${S3_BUCKET_MEDIA:-racket-media}"
REGION="us-east-1"

die() { echo "dev-objectstore: $*" >&2; exit 1; }

# weed exits with this log line when another process holds one of its ports (main run
# 40874800467). Only this failure is retried, on fresh ports; anything else fails closed.
BIND_COLLISION="address already in use"
MAX_PORT_RETRIES=3
WEED_PORTS=8 # master, volume, filer, s3; each with its gRPC port

# Prints N distinct free 127.0.0.1 ports. All sockets stay bound until every port is chosen,
# so one allocation can never repeat a port (CI-OBJSTORE-PORT-RACE). Another process can
# still take one before weed binds it; start_weed_once reports that as a collision.
alloc_ports() {
  [[ "${1:-}" =~ ^[1-9][0-9]*$ ]] || { echo "dev-objectstore: ports needs a positive count" >&2; return 2; }
  python3 - "$1" <<'PY'
import socket
import sys

socks = []
try:
    for _ in range(int(sys.argv[1])):
        s = socket.socket()
        socks.append(s)
        s.bind(("127.0.0.1", 0))
    print(" ".join(str(s.getsockname()[1]) for s in socks))
finally:
    for s in socks:
        s.close()
PY
}

weed_bin() {
  if [[ -n "${WEED_BIN:-}" ]]; then echo "$WEED_BIN"; return; fi
  if command -v weed >/dev/null 2>&1; then command -v weed; return; fi
  local bin="$CACHE_BIN/weed-$WEED_VERSION"
  if [[ ! -x "$bin" ]]; then
    [[ "$(uname -s)-$(uname -m)" == "Linux-x86_64" ]] \
      || die "no pinned download for $(uname -s)-$(uname -m); install SeaweedFS $WEED_VERSION and set WEED_BIN"
    mkdir -p "$CACHE_BIN"
    # Parallel test workers (pytest-xdist, CI-INFRA-BUDGET) share this cache: download one at a
    # time, and re-check under the lock so only the first worker fetches. The lock is released
    # when this function's subshell exits, also on die.
    exec 9>"$CACHE_BIN/.weed-download.lock"
    flock 9
    if [[ ! -x "$bin" ]]; then
      local tgz="$CACHE_BIN/weed-$WEED_VERSION.tgz"
      echo "dev-objectstore: downloading SeaweedFS $WEED_VERSION" >&2
      curl -fsSL -o "$tgz" \
        "https://github.com/seaweedfs/seaweedfs/releases/download/$WEED_VERSION/linux_amd64.tar.gz" \
        || { rm -f "$tgz"; die "download failed (see docs/process/ci-cd.md, 'Local services without Docker')"; }
      echo "$WEED_SHA256_LINUX_AMD64  $tgz" | sha256sum -c --quiet - \
        || { rm -f "$tgz"; die "sha256 mismatch for SeaweedFS download; refusing to run it"; }
      tar -xzf "$tgz" -C "$CACHE_BIN" weed
      mv "$CACHE_BIN/weed" "$bin"
      rm -f "$tgz"
    fi
    exec 9>&-
  fi
  echo "$bin"
}

load_state() {
  [[ -f "$STATE_FILE" ]] || return 1
  # shellcheck disable=SC1090
  source "$STATE_FILE"
}

is_running() { load_state && kill -0 "$PID" 2>/dev/null; }

print_env() {
  cat <<ENV
export S3_ENDPOINT_URL=$ENDPOINT
export S3_ACCESS_KEY_ID=$ACCESS_KEY
export S3_SECRET_ACCESS_KEY=$SECRET_KEY
export S3_REGION=$REGION
export S3_BUCKET_MEDIA=$BUCKET
ENV
}

s3_put_bucket() {
  curl -s -o /dev/null -w '%{http_code}' --max-time 5 -X PUT \
    --aws-sigv4 "aws:amz:$REGION:s3" --user "$ACCESS_KEY:$SECRET_KEY" "$ENDPOINT/$BUCKET" || true
}

# Starts weed once on freshly allocated ports and waits for S3. Returns 0 when the bucket
# exists and 75 when weed died of a port collision; every other failure dies (fail closed).
start_weed_once() {
  local bin="$1" ports m_port m_grpc v_port v_grpc f_port f_grpc s3_port s3_grpc
  ports="$(alloc_ports "$WEED_PORTS")" || die "could not allocate $WEED_PORTS free ports"
  read -r m_port m_grpc v_port v_grpc f_port f_grpc s3_port s3_grpc <<<"$ports"
  [[ -n "$s3_grpc" ]] || die "port allocation returned '$ports'"

  # Called from an `||` list, so set -e is off in here: every step that can fail says so.
  DATA="$(mktemp -d "${TMPDIR:-/tmp}/racket-s3.XXXXXX")" || die "mktemp failed"
  ENDPOINT="http://127.0.0.1:$s3_port"
  cat > "$DATA/s3.json" <<JSON
{"identities": [{"name": "racket-dev",
  "credentials": [{"accessKey": "$ACCESS_KEY", "secretKey": "$SECRET_KEY"}],
  "actions": ["Admin", "Read", "Write", "List", "Tagging"]}]}
JSON
  chmod 600 "$DATA/s3.json" || die "could not write $DATA/s3.json"

  nohup "$bin" server -ip=127.0.0.1 -ip.bind=127.0.0.1 -dir="$DATA" \
    -master.port="$m_port" -master.port.grpc="$m_grpc" -master.volumeSizeLimitMB=64 \
    -volume.port="$v_port" -volume.port.grpc="$v_grpc" -volume.max=0 \
    -filer -filer.port="$f_port" -filer.port.grpc="$f_grpc" \
    -s3 -s3.port="$s3_port" -s3.port.grpc="$s3_grpc" -s3.config="$DATA/s3.json" \
    > "$DATA/weed.log" 2>&1 &
  PID=$!

  mkdir -p "$STATE_DIR" || die "could not create $STATE_DIR"
  umask 077
  cat > "$STATE_FILE" <<STATE || die "could not write $STATE_FILE"
PID='$PID'
DATA='$DATA'
ENDPOINT='$ENDPOINT'
ACCESS_KEY='$ACCESS_KEY'
SECRET_KEY='$SECRET_KEY'
BUCKET='$BUCKET'
STATE

  local code="" i
  for i in $(seq 1 120); do
    if ! kill -0 "$PID" 2>/dev/null; then
      tail -20 "$DATA/weed.log" >&2
      grep -q "$BIND_COLLISION" "$DATA/weed.log" && return 75
      die "weed exited during startup"
    fi
    code="$(s3_put_bucket)"
    [[ "$code" == "200" || "$code" == "409" ]] && return 0
    sleep 0.5
  done
  : "$i"
  tail -20 "$DATA/weed.log" >&2
  die "S3 not ready (last HTTP $code)"
}

cmd_start() {
  if is_running; then print_env; return 0; fi
  [[ -f "$STATE_FILE" ]] && cmd_stop >/dev/null 2>&1 || true
  local bin attempt rc
  bin="$(weed_bin)"
  ACCESS_KEY="dev$(python3 -c 'import secrets; print(secrets.token_hex(8))')"
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(20))')"

  for attempt in $(seq 0 "$MAX_PORT_RETRIES"); do
    rc=0
    start_weed_once "$bin" || rc=$?
    [[ "$rc" == 0 ]] && { print_env; return 0; }
    [[ "$rc" == 75 ]] || die "weed exited during startup"
    rm -rf "$DATA"
    rm -f "$STATE_FILE"
    (( attempt < MAX_PORT_RETRIES )) \
      || die "weed exited during startup ($BIND_COLLISION on every try, $MAX_PORT_RETRIES retries)"
    echo "dev-objectstore: port collision, retry $((attempt + 1))/$MAX_PORT_RETRIES with fresh ports" >&2
  done
}

cmd_stop() {
  if load_state; then
    kill "$PID" 2>/dev/null || true
    for _ in $(seq 1 20); do kill -0 "$PID" 2>/dev/null || break; sleep 0.25; done
    kill -9 "$PID" 2>/dev/null || true
    rm -rf "$DATA"
    rm -f "$STATE_FILE"
    echo "dev-objectstore: stopped and removed $DATA"
  else
    echo "dev-objectstore: nothing to stop"
  fi
}

case "${1:-}" in
  start) cmd_start ;;
  stop) cmd_stop ;;
  env) is_running || die "not running"; print_env ;;
  ports) alloc_ports "${2:-}" ;;
  status) if is_running; then echo "running at $ENDPOINT (pid $PID)"; else echo "not running"; exit 1; fi ;;
  *) echo "usage: $0 start|stop|env|status|ports N" >&2; exit 2 ;;
esac
