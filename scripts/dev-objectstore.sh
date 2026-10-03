#!/usr/bin/env bash
# Local S3-compatible object store without Docker: SeaweedFS (ADR 0008 part C), ST-001.
#
#   eval "$(scripts/dev-objectstore.sh start)"   # exports S3_* variables
#   scripts/dev-objectstore.sh env | status | stop
#
# Downloads a pinned SeaweedFS release (sha256-verified) into <repo>/.local/bin unless
# WEED_BIN or `weed` on PATH is available. Binds 127.0.0.1 only, on free ports, with
# random per-instance credentials, and creates the media bucket. `stop` deletes the data.
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

free_port() {
  python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
}

weed_bin() {
  if [[ -n "${WEED_BIN:-}" ]]; then echo "$WEED_BIN"; return; fi
  if command -v weed >/dev/null 2>&1; then command -v weed; return; fi
  local bin="$CACHE_BIN/weed-$WEED_VERSION"
  if [[ ! -x "$bin" ]]; then
    [[ "$(uname -s)-$(uname -m)" == "Linux-x86_64" ]] \
      || die "no pinned download for $(uname -s)-$(uname -m); install SeaweedFS $WEED_VERSION and set WEED_BIN"
    mkdir -p "$CACHE_BIN"
    local tgz="$CACHE_BIN/weed-$WEED_VERSION.tgz"
    echo "dev-objectstore: downloading SeaweedFS $WEED_VERSION" >&2
    curl -fsSL -o "$tgz" \
      "https://github.com/seaweedfs/seaweedfs/releases/download/$WEED_VERSION/linux_amd64.tar.gz" \
      || die "download failed (see docs/process/ci-cd.md, 'Local services without Docker')"
    echo "$WEED_SHA256_LINUX_AMD64  $tgz" | sha256sum -c --quiet - \
      || { rm -f "$tgz"; die "sha256 mismatch for SeaweedFS download; refusing to run it"; }
    tar -xzf "$tgz" -C "$CACHE_BIN" weed
    mv "$CACHE_BIN/weed" "$bin"
    rm -f "$tgz"
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

cmd_start() {
  if is_running; then print_env; return 0; fi
  [[ -f "$STATE_FILE" ]] && cmd_stop >/dev/null 2>&1 || true
  local bin
  bin="$(weed_bin)"

  DATA="$(mktemp -d "${TMPDIR:-/tmp}/racket-s3.XXXXXX")"
  ACCESS_KEY="dev$(python3 -c 'import secrets; print(secrets.token_hex(8))')"
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(20))')"
  local s3_port
  s3_port="$(free_port)"
  ENDPOINT="http://127.0.0.1:$s3_port"
  cat > "$DATA/s3.json" <<JSON
{"identities": [{"name": "racket-dev",
  "credentials": [{"accessKey": "$ACCESS_KEY", "secretKey": "$SECRET_KEY"}],
  "actions": ["Admin", "Read", "Write", "List", "Tagging"]}]}
JSON
  chmod 600 "$DATA/s3.json"

  nohup "$bin" server -ip=127.0.0.1 -ip.bind=127.0.0.1 -dir="$DATA" \
    -master.port="$(free_port)" -master.port.grpc="$(free_port)" -master.volumeSizeLimitMB=64 \
    -volume.port="$(free_port)" -volume.port.grpc="$(free_port)" -volume.max=0 \
    -filer -filer.port="$(free_port)" -filer.port.grpc="$(free_port)" \
    -s3 -s3.port="$s3_port" -s3.port.grpc="$(free_port)" -s3.config="$DATA/s3.json" \
    > "$DATA/weed.log" 2>&1 &
  PID=$!

  mkdir -p "$STATE_DIR"
  umask 077
  cat > "$STATE_FILE" <<STATE
PID='$PID'
DATA='$DATA'
ENDPOINT='$ENDPOINT'
ACCESS_KEY='$ACCESS_KEY'
SECRET_KEY='$SECRET_KEY'
BUCKET='$BUCKET'
STATE

  local code="" i
  for i in $(seq 1 120); do
    kill -0 "$PID" 2>/dev/null || { tail -20 "$DATA/weed.log" >&2; die "weed exited during startup"; }
    code="$(s3_put_bucket)"
    [[ "$code" == "200" || "$code" == "409" ]] && break
    sleep 0.5
  done
  [[ "$code" == "200" || "$code" == "409" ]] || { tail -20 "$DATA/weed.log" >&2; die "S3 not ready (last HTTP $code)"; }
  : "$i"
  print_env
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
  status) if is_running; then echo "running at $ENDPOINT (pid $PID)"; else echo "not running"; exit 1; fi ;;
  *) echo "usage: $0 start|stop|env|status" >&2; exit 2 ;;
esac
