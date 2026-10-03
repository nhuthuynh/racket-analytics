#!/usr/bin/env bash
# Throwaway local Postgres 16 cluster without Docker (ST-001).
#
#   eval "$(scripts/dev-postgres.sh start)"   # exports DATABASE_URL
#   scripts/dev-postgres.sh url | status | stop
#
# Real server on 127.0.0.1, a free TCP port, scram-sha-256 password auth and a random
# password per cluster: the same backing service as production, never SQLite [AQS/OPS-05].
# The data directory is a temp dir and `stop` deletes it. When run as root (dev
# containers), the server runs as the `postgres` OS user because initdb refuses root.
#
# Env: PG_BIN (default: /usr/lib/postgresql/16/bin, else `pg_config --bindir`),
#      RA_DEV_STATE (default: <repo>/.local), PG_DB (default: racket), PG_USER (racket).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${RA_DEV_STATE:-$ROOT/.local}"
STATE_FILE="$STATE_DIR/postgres.state"
PG_DB="${PG_DB:-racket}"
PG_USER="${PG_USER:-racket}"

die() { echo "dev-postgres: $*" >&2; exit 1; }

pg_bin() {
  if [[ -n "${PG_BIN:-}" ]]; then echo "$PG_BIN"; return; fi
  if [[ -x /usr/lib/postgresql/16/bin/initdb ]]; then echo /usr/lib/postgresql/16/bin; return; fi
  if command -v pg_config >/dev/null 2>&1; then pg_config --bindir; return; fi
  echo /usr/lib/postgresql/16/bin
}

free_port() {
  python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
}

as_owner() {
  if [[ "$(id -u)" -eq 0 ]]; then
    id postgres >/dev/null 2>&1 || die "running as root needs a 'postgres' OS user (initdb refuses root)"
    runuser -u postgres -- "$@"
  else
    "$@"
  fi
}

load_state() {
  [[ -f "$STATE_FILE" ]] || return 1
  # shellcheck disable=SC1090
  source "$STATE_FILE"
}

is_running() {
  load_state || return 1
  as_owner "$BIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1
}

print_url() {
  echo "export DATABASE_URL=$URL"
  echo "# PGDATA=$PGDATA"
}

cmd_start() {
  if is_running; then print_url; return 0; fi
  [[ -f "$STATE_FILE" ]] && cmd_stop >/dev/null 2>&1 || true

  BIN="$(pg_bin)"
  [[ -x "$BIN/initdb" ]] || die "initdb not found in $BIN (install postgresql-16 or set PG_BIN)"
  local version
  version="$("$BIN/postgres" --version | awk '{print $3}')"
  [[ "$version" == 16* ]] || echo "dev-postgres: warning: Postgres $version, production uses 16" >&2

  local tmp_root="${TMPDIR:-/tmp}"
  [[ "$(id -u)" -eq 0 ]] && tmp_root=/tmp  # the postgres user must be able to reach it
  PGDATA="$(mktemp -d "$tmp_root/racket-pg.XXXXXX")"
  local pwfile="$PGDATA.pw"
  local password
  password="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
  PORT="$(free_port)"
  printf '%s\n' "$password" > "$pwfile"
  if [[ "$(id -u)" -eq 0 ]]; then
    chown postgres:postgres "$PGDATA" "$pwfile"
  fi
  chmod 700 "$PGDATA"
  chmod 600 "$pwfile"

  as_owner "$BIN/initdb" -D "$PGDATA" -U "$PG_USER" --pwfile="$pwfile" \
    --auth-local=scram-sha-256 --auth-host=scram-sha-256 -E UTF8 --locale=C.UTF-8 >/dev/null \
    || { rm -rf "$PGDATA" "$pwfile"; die "initdb failed"; }
  rm -f "$pwfile"

  as_owner "$BIN/pg_ctl" -D "$PGDATA" -l "$PGDATA/server.log" -w -t 30 \
    -o "-c listen_addresses=127.0.0.1 -p $PORT -k $PGDATA -c fsync=off -c full_page_writes=off" \
    start >/dev/null || { cat "$PGDATA/server.log" >&2; die "server did not start"; }

  PGPASSWORD="$password" "$BIN/psql" -h 127.0.0.1 -p "$PORT" -U "$PG_USER" -d postgres -qAt \
    -c "CREATE DATABASE \"$PG_DB\"" >/dev/null || die "could not create database $PG_DB"

  URL="postgresql://$PG_USER:$password@127.0.0.1:$PORT/$PG_DB"
  mkdir -p "$STATE_DIR"
  umask 077
  cat > "$STATE_FILE" <<STATE
BIN='$BIN'
PGDATA='$PGDATA'
PORT='$PORT'
URL='$URL'
STATE
  print_url
}

cmd_stop() {
  if load_state; then
    as_owner "$BIN/pg_ctl" -D "$PGDATA" -m immediate -w stop >/dev/null 2>&1 || true
    rm -rf "$PGDATA"
    rm -f "$STATE_FILE"
    echo "dev-postgres: stopped and removed $PGDATA"
  else
    echo "dev-postgres: nothing to stop"
  fi
}

cmd_url() {
  is_running || die "not running (start it with: eval \"\$(scripts/dev-postgres.sh start)\")"
  print_url
}

case "${1:-}" in
  start) cmd_start ;;
  stop) cmd_stop ;;
  url) cmd_url ;;
  status) if is_running; then echo "running on port $PORT"; else echo "not running"; exit 1; fi ;;
  *) echo "usage: $0 start|stop|url|status" >&2; exit 2 ;;
esac
